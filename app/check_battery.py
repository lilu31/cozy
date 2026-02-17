from sqlmodel import Session, select
from backend.database import engine
from backend.models import Asset, AssetType

def check_battery():
    with Session(engine) as session:
        battery = session.exec(select(Asset).where(Asset.asset_type == AssetType.BATTERY)).first()
        if battery:
            print(f"Battery ID: {battery.id}")
            print(f"Name: {battery.display_name}")
            print(f"Capacity: {battery.capacity_kwh} kWh")
            print(f"Max Power: {battery.max_power_kw} kW")
        else:
            print("No Battery Found!")

if __name__ == "__main__":
    check_battery()
