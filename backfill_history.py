import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from sqlmodel import Session, select
from backend.database import engine
from backend.models import MeterReading, MarketPrice, Asset, AssetType, User
from backend.services.optimization.solver import HomeEnergySolver

# Ensure backend imports work
# We are running from project root or app/
sys.path.append(os.getcwd())

def backfill_optimization():
    print("--- Backfilling History with AI Strategy ---")
    
    with Session(engine) as session:
        # 1. Setup Context
        user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
        if not user:
            print("User not found.")
            return

        battery = session.exec(select(Asset).where(Asset.asset_type == AssetType.BATTERY)).first()
        pv = session.exec(select(Asset).where(Asset.asset_type == AssetType.PV)).first()
        
        if not battery or not pv:
            print("Missing assets.")
            return

        # 2. Define Window (Last 14 days)
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        # Look back 14 days to ensure plenty of history
        start = now - timedelta(days=14)
        
        print(f"Optimizing Window: {start} to {now}")
        
        # 3. Fetch Input Data (Prices & PV)
        # Prices
        prices = session.exec(select(MarketPrice).where(
            MarketPrice.timestamp >= start,
            MarketPrice.timestamp < now
        ).order_by(MarketPrice.timestamp)).all()
        
        if not prices:
             print("No prices found for window.")
             return
             
        # PV Readings (Use existing generation as 'forecast' / actuals)
        pv_readings = session.exec(select(MeterReading).where(
            MeterReading.timestamp >= start,
            MeterReading.timestamp < now,
            MeterReading.asset_id == pv.id
        ).order_by(MeterReading.timestamp)).all()
        
        # 4. Construct Vectors
        # Map to 15min timestamps
        timestamps = pd.date_range(start=start, end=now - timedelta(minutes=15), freq='15T')
        horizon = len(timestamps)
        
        print(f"Horizon Steps: {horizon}")
        
        price_map = {p.timestamp: p.price_eur_per_mwh for p in prices}
        pv_map = {r.timestamp: r.power_kw for r in pv_readings}
        
        price_vec = []
        net_load_vec = [] # Load - PV
        
        base_load = 0.5 # Assumption
        
        # Fill missing with safe defaults
        for ts in timestamps:
            p = price_map.get(ts, 100.0) # Default 100 EUR/MWh
            sol = pv_map.get(ts, 0.0)
            
            price_vec.append(p)
            net_load_vec.append(base_load - sol)
            
        # 5. Solve
        solver = HomeEnergySolver()
        specs = {
            'battery': {
                'capacity': battery.capacity_kwh,
                'max_power': battery.max_power_kw,
                'eff': 0.95
            }
        }
        
        solution = solver.solve(
            horizon=horizon,
            prices=price_vec,
            net_loads=net_load_vec,
            asset_specs=specs,
            initial_soc=5.0 # Start from 50% assumption at beginning of window
        )
        
        if solution.empty:
            print("Solver failed.")
            return
            
        # 6. Update DB
        print("Updating Database...")
        updated_count = 0
        
        for i, row in solution.iterrows():
            ts = timestamps[int(row['step'])]
            
            # Battery Power
            bat_power = float(row['bat_discharge_kw'] - row['bat_charge_kw'])
            soc_kwh = float(row['soc_kwh'])
            soc_percent = (soc_kwh / battery.capacity_kwh) * 100.0
            
            # Upsert (Create or Update)
            # We enforce clean 15-min aligned timestamps for the optimized history.
            
            # Create object (SQLModel will update if PK exists, or insert)
            new_reading = MeterReading(
                timestamp=ts,
                asset_id=battery.id,
                power_kw=bat_power,
                soc_percent=soc_percent
            )
            session.merge(new_reading)
            updated_count += 1
                
        session.commit()
        print(f"Upserted {updated_count} battery records with Optimal Strategy.")
                
        session.commit()
        print(f"Updated {updated_count} battery readings with Optimal Strategy.")

if __name__ == "__main__":
    backfill_optimization()
