from sqlmodel import Session, select
from backend.database import engine
from backend.models import MeterReading, Asset, AssetType

def fix_history():
    print("Repairing Battery History...")
    with Session(engine) as session:
        # Find Battery
        battery = session.exec(select(Asset).where(Asset.asset_type == AssetType.BATTERY)).first()
        if not battery:
            print("No battery found.")
            return

        print(f"Battery: {battery.display_name} ({battery.capacity_kwh} kWh)")
        
        # Get Readings Sorted
        readings = session.exec(select(MeterReading).where(MeterReading.asset_id == battery.id).order_by(MeterReading.timestamp)).all()
        
        current_soc_percent = 50.0 # Assumption for start of history
        capacity = battery.capacity_kwh
        
        modified_count = 0
        
        for r in readings:
            # Re-calculate limits based on SOC at START of step
            current_energy = (current_soc_percent / 100.0) * capacity
            
            original_power = r.power_kw
            new_power = original_power
            
            # Check limits
            if original_power < 0: # Charge
                headroom = capacity - current_energy
                max_accept = headroom / 0.25
                if abs(original_power) > max_accept:
                    new_power = -max_accept # Clamp
            elif original_power > 0: # Discharge
                available = current_energy
                max_provide = available / 0.25
                if original_power > max_provide:
                    new_power = max_provide # Clamp
            
            # Update SOC for next step
            energy_change = new_power * 0.25
            current_energy -= energy_change # Subtract consumption
            
            # Safety Clamp state
            current_energy = max(0.0, min(capacity, current_energy))
            current_soc_percent = (current_energy / capacity) * 100.0
            
            # Update Record
            if abs(new_power - original_power) > 0.001 or abs(r.soc_percent - current_soc_percent) > 0.1:
                r.power_kw = new_power
                r.soc_percent = current_soc_percent
                session.add(r)
                modified_count += 1
                
        session.commit()
        print(f"Repaired {modified_count} records.")

if __name__ == "__main__":
    fix_history()
