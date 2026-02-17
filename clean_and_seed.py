import sys
import random
import math
from datetime import datetime, timedelta
from sqlmodel import Session, select, delete
from backend.database import engine
from backend.models import MeterReading, MarketPrice, Asset, AssetType, User

sys.path.append("/Users/linus_privat/.gemini/antigravity/playground/plasma-ring")

def clean_and_seed():
    print("--- Cleaning and Reseeding History ---")
    
    with Session(engine) as session:
        # 1. Clear History
        # We keep Assets and Users, but clear Readings and Prices
        print("Truncating partial history...")
        session.exec(delete(MeterReading))
        session.exec(delete(MarketPrice))
        session.commit()
        
        # 2. Get Assets
        user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
        pv = session.exec(select(Asset).where(Asset.asset_type == AssetType.PV)).first()
        battery = session.exec(select(Asset).where(Asset.asset_type == AssetType.BATTERY)).first()
        ev = session.exec(select(Asset).where(Asset.asset_type == AssetType.EV)).first()
        
        # 3. Generate Time Range (Dec 1 to Now + 1 day forecast)
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        start = now.replace(day=1, hour=0, minute=0, second=0)
        end = now + timedelta(hours=24)
        
        print(f"Seeding from {start} to {end}")
        
        timestamps = []
        curr = start
        while curr < end:
            timestamps.append(curr)
            curr += timedelta(minutes=15)
            
        print(f"Steps: {len(timestamps)}")
        
        # 4. Generate Data
        new_prices = []
        new_readings = []
        
        for ts in timestamps:
            # Price (Peak at 8am and 7pm)
            hour = ts.hour + ts.minute/60.0
            price_base = 0.25 # 25ct
            price_var = 0.10 * math.sin((hour - 6) * math.pi / 12) # Swing
            price_rand = random.uniform(-0.02, 0.02)
            final_price = max(0.05, min(0.50, price_base + price_var + price_rand))
            
            new_prices.append(MarketPrice(
                timestamp=ts,
                price_eur_per_mwh=final_price * 1000.0
            ))
            
            # PV (Bell curve centered at 13:00)
            pv_power = 0.0
            if 6 < hour < 20:
                peak = 5.0 # 5kW peak
                # Normalized bell curve
                pv_power = peak * math.exp(-((hour - 13) ** 2) / 8)
                pv_power += random.uniform(-0.2, 0.2)
                pv_power = max(0.0, pv_power)
                
            new_readings.append(MeterReading(
                timestamp=ts,
                asset_id=pv.id,
                power_kw=pv_power
            ))
            
            # Initialize Empty Battery Reading (Will be backfilled by AI)
            # But we need SOMETHING for the gap check? 
            # No, backfill script will create them.
            # But "Dashboard" expects readings.
            # Let's Seed "Dumb" battery (0 idle) so we have a base.
            new_readings.append(MeterReading(
                timestamp=ts,
                asset_id=battery.id,
                power_kw=0.0,
                soc_percent=50.0
            ))
            
        # Bulk Insert
        print("Bulk Saving...")
        session.add_all(new_prices)
        session.add_all(new_readings)
        session.commit()
        print("Data Cleaned and Seeded.")

if __name__ == "__main__":
    clean_and_seed()
