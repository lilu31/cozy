from datetime import datetime, timedelta
import random
import math
from sqlmodel import Session, select
from database import engine
from models import User, Tenant, Asset, AssetType, MeterReading, MarketPrice

def generate_sine_wave(timestamp: datetime, period_hours: float, amplitude: float, offset: float, noise_factor: float = 0.1) -> float:
    """Generates a value based on a sine wave with noise."""
    seconds = (timestamp - timestamp.replace(hour=0, minute=0, second=0)).total_seconds()
    # 2*pi * time / period
    val = amplitude * math.sin(2 * math.pi * seconds / (period_hours * 3600)) + offset
    noise = random.uniform(-noise_factor * amplitude, noise_factor * amplitude)
    return max(0, val + noise)

def generate_pv_output(timestamp: datetime, capacity_kw: float) -> float:
    """Generates PV output (bell curve roughly between 6am and 8pm)."""
    hour = timestamp.hour + timestamp.minute / 60
    if 6 <= hour <= 20:
        # Peak around 13:00
        # Simple parabolic shape: y = -a(x-h)^2 + k
        # or sine part. Let's use sine for simplicity, mapped to 6-20.
        # Center 13, Width ~14h.
        normalized_pos = (hour - 6) / 14 * math.pi # 0 to pi
        val = capacity_kw * math.sin(normalized_pos)
        noise = random.uniform(-0.05 * capacity_kw, 0.05 * capacity_kw)
        return max(0, val + noise)
    return 0.0

def seed_data():
    with Session(engine) as session:
        print("Checking for existing data...")
        existing_user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
        if existing_user:
            print("Data already seems to exist. Skipping seed.")
            return

        print("Creating User and Assets...")
        # 1. User & Tenant
        user = User(email="test@cozy.io", full_name="Test User")
        session.add(user)
        session.commit()
        session.refresh(user)

        tenant = Tenant(user_id=user.id, address="Musterstraße 1, Berlin")
        session.add(tenant)
        
        # 2. Assets
        # PV
        pv = Asset(
            user_id=user.id,
            asset_type=AssetType.PV,
            display_name="Rooftop Solar",
            max_power_kw=8.0
        )
        session.add(pv)
        
        # Battery
        battery = Asset(
            user_id=user.id,
            asset_type=AssetType.BATTERY,
            display_name="Home Battery",
            capacity_kwh=10.0,
            max_power_kw=5.0
        )
        session.add(battery)

        # EV
        ev = Asset(
            user_id=user.id,
            asset_type=AssetType.EV,
            display_name="Tesla Model Y",
            capacity_kwh=75.0,
            max_power_kw=11.0
        )
        session.add(ev)
        
        session.commit()
        session.refresh(pv)
        session.refresh(battery)
        session.refresh(ev)
        
        print(f"Created Assets: {pv.id}, {battery.id}, {ev.id}")

        # 3. Time Series Data (Past 7 days)
        print("Generating 7 days of historical data...")
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        delta = timedelta(minutes=15)
        
        curr = start_date
        readings = []
        prices = []
        
        battery_soc = 50.0 # Start at 50%
        
        while curr < end_date:
            # Market Price (Sine wave, peak evening, low midday)
            # Inverse of solar usually? Or typical duck curve.
            # Let's say high morning/evening, low midday.
            # Super loose approx: Sine with 12h period? No, 24h.
            # Prices: 15-40 ct/kWh -> 150 - 400 EUR/MWh
            # Peak at 8am and 7pm.
            hour = curr.hour
            base_price = 250.0 
            if 7 <= hour <= 9 or 17 <= hour <= 20:
                price_val = base_price + random.uniform(50, 150)
            elif 11 <= hour <= 15: # Solar dip
                price_val = base_price - random.uniform(50, 150)
            else:
                price_val = base_price + random.uniform(-20, 20)
                
            prices.append(MarketPrice(timestamp=curr, price_eur_per_mwh=max(0, price_val)))

            # PV Generation
            pv_gen = generate_pv_output(curr, 8.0)
            # Power is positive for production? 
            # Request says: Negative = Charging/Consuming, Positive = Discharging/Producing
            readings.append(MeterReading(timestamp=curr, asset_id=pv.id, power_kw=pv_gen))

            # Battery Logic (Smart Limit)
            bat_power = 0.0
            
            # Metadata
            capacity = 10.0
            max_charge_rate = 5.0
            # Current Energy
            current_energy = (battery_soc / 100.0) * capacity
            
            if pv_gen > 1.0: # Charge Mode
                # Available headroom
                headroom_kwh = capacity - current_energy
                # Max power we can accept in 15 mins (0.25h)
                max_accept_kw = headroom_kwh / 0.25
                
                target_power = min(pv_gen, max_charge_rate)
                actual_power = min(target_power, max_accept_kw)
                
                bat_power = -actual_power # Negative = Charging
                
            else: # Discharge Mode
                # Available energy
                available_kwh = current_energy
                # Max power we can provide
                max_provide_kw = available_kwh / 0.25
                
                target_power = 0.5 # Slow drain
                actual_power = min(target_power, max_provide_kw)
                
                bat_power = actual_power # Positive = Discharging

            # Update SoC
            energy_change_kwh = bat_power * 0.25
            # Charge (neg power) -> neg change. But we subtract consumption? 
            # Wait, consistent from before:
            # battery_soc_kwh -= energy_change_kwh
            # if bat_power = -5, change = -1.25. soc -= -1.25 => soc += 1.25. Correct.
            
            current_energy -= energy_change_kwh
            
            # Safety Clamp
            current_energy = max(0, min(capacity, current_energy))
            battery_soc = (current_energy / capacity) * 100.0
            
            readings.append(MeterReading(
                timestamp=curr, 
                asset_id=battery.id, 
                power_kw=bat_power, 
                soc_percent=battery_soc
            ))

            # EV Logic
            # Plug in at 18:00, charge for 4 hours.
            ev_power = 0.0
            if 18 <= hour < 22:
                ev_power = -11.0 # Max charging
            readings.append(MeterReading(timestamp=curr, asset_id=ev.id, power_kw=ev_power))

            curr += delta

        # Batch insert for speed
        print(f"Inserting {len(prices)} price records and {len(readings)} readings...")
        session.add_all(prices)
        session.add_all(readings)
        session.commit()
        print("Done!")

if __name__ == "__main__":
    seed_data()
