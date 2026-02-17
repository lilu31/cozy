import asyncio
import sys
import os
sys.path.append(os.getcwd())
from sqlmodel import Session, select, func
from backend.database import engine
from backend.models import Asset, AssetDispatchSchedule, MarketPrice, MeterReading

def analyze_data():
    with Session(engine) as session:
        # 1. Check Assets and their Types
        assets = session.exec(select(Asset)).all()
        print("\n--- ASSETS ---")
        for a in assets:
            print(f"ID: {a.id}, Name: {a.display_name}, Type: '{a.asset_type}'")
            
        # 2. Check Schedule Counts by Asset
        print("\n--- SCHEDULE COUNTS ---")
        for a in assets:
            count = session.exec(select(func.count()).where(AssetDispatchSchedule.asset_id == a.id)).one()
            avg_power = session.exec(select(func.avg(AssetDispatchSchedule.planned_power_kw)).where(AssetDispatchSchedule.asset_id == a.id)).one()
            print(f"Asset: {a.display_name}, Count: {count}, Avg Power: {avg_power}")
            
            # Show first 5 non-zero entries
            entries = session.exec(select(AssetDispatchSchedule).where(AssetDispatchSchedule.asset_id == a.id).where(AssetDispatchSchedule.planned_power_kw != 0).limit(5)).all()
            if entries:
                print(f"  First 5 Non-Zero for {a.display_name}:")
                for e in entries:
                    print(f"    {e.timestamp}: {e.planned_power_kw} kW")
            else:
                print(f"  NO Non-Zero entries for {a.display_name}")

if __name__ == "__main__":
    analyze_data()
