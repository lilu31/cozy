from backend.infrastructure.mocks.asset_mock import MockAssetAdapter
from backend.models import AssetType
from uuid import uuid4

def test_physics():
    print("Testing Physics Engine...")
    adapter = MockAssetAdapter()
    
    # Create a Battery
    bat_id = uuid4()
    battery_state = adapter._get_or_create_state(bat_id, AssetType.BATTERY, capacity=10.0)
    battery_state.soc_percent = 50.0 # 5kWh
    
    print(f"Initial SoC: {battery_state.soc_percent}% (5.0 kWh)")
    
    # 1. Test Charging (Negative Power)
    # Charge at 5kW for 1 hour (4 x 15min steps)
    # Expected: +5kWh -> 10kWh (100%)
    adapter.dispatch(bat_id, -5.0)
    
    for i in range(4):
        adapter.simulate_physics_step(minutes=15)
        telem = adapter.get_telemetry(bat_id)
        print(f"Step {i+1} (Charge): SoC={telem['soc_percent']:.2f}% | Power={telem['power_kw']:.2f}kW")
        
    assert battery_state.soc_percent >= 99.0, f"Battery should be full, got {battery_state.soc_percent}"
    print("Charging Test Passed ✅")
    
    # 2. Test Discharging (Positive Power)
    # Discharge at 5kW for 30 mins
    # Expected: -2.5kWh -> 7.5kWh (75%)
    adapter.dispatch(bat_id, 5.0)
    
    for i in range(2):
        adapter.simulate_physics_step(minutes=15)
        telem = adapter.get_telemetry(bat_id)
        print(f"Step {i+1} (Discharge): SoC={telem['soc_percent']:.2f}%")
        
    assert 74.0 <= battery_state.soc_percent <= 76.0, f"Battery should be ~75%, got {battery_state.soc_percent}"
    print("Discharging Test Passed ✅")

if __name__ == "__main__":
    test_physics()
