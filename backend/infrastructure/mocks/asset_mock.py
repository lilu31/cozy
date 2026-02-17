import random
from datetime import datetime
from uuid import UUID
from typing import Dict, Any, Optional
from ..interfaces import IAssetAdapter
from ...models import AssetType

class AssetMockState:
    def __init__(self, asset_type: AssetType, capacity_kwh: float = 0.0):
        self.asset_type = asset_type
        self.capacity_kwh = capacity_kwh
        self.soc_percent = 50.0  # Default start
        self.connected = True
        self.last_dispatch_kw = 0.0
        
        # EV Specifics: Plugged in schedule (18:00 - 08:00 normally)
        self.is_ev_plugged_in = True 

class MockAssetAdapter(IAssetAdapter):
    def __init__(self):
        self._states: Dict[UUID, AssetMockState] = {}

    def _get_or_create_state(self, asset_id: UUID, asset_type: AssetType, capacity: float) -> AssetMockState:
        if asset_id not in self._states:
            self._states[asset_id] = AssetMockState(asset_type, capacity)
        return self._states[asset_id]

    # --- Interface Implementation ---
    
    def get_telemetry(self, asset_id: UUID) -> Dict[str, Any]:
        """Returns live telemetry from the physics engine."""
        if asset_id not in self._states:
            return {"power_kw": 0.0, "soc_percent": 0.0}
        
        state = self._states[asset_id]
        
        # Add some sensor noise
        noise = random.uniform(-0.1, 0.1)
        
        return {
            "power_kw": state.last_dispatch_kw + noise,
            "soc_percent": state.soc_percent,
            "connected": state.connected
        }

    def dispatch(self, asset_id: UUID, power_kw: float) -> bool:
        """Sets the setpoint for the next step."""
        if asset_id in self._states:
            self._states[asset_id].last_dispatch_kw = power_kw
            return True
        return False

    # --- Physics Simulation ---

    def simulate_physics_step(self, minutes: int = 15):
        """
        Advances the state of all assets by `minutes`.
        Call this periodically in the background loop.
        """
        current_hour = datetime.utcnow().hour
        
        for asset_id, state in self._states.items():
            # 1. Update Connection Status (EV only)
            if state.asset_type == AssetType.EV:
                # Simple logic: Home between 18:00 and 08:00
                if 18 <= current_hour or current_hour < 8:
                    state.connected = True
                else:
                    state.connected = False  # Driving
            
            # 2. Apply Physics if connected
            if state.connected and state.capacity_kwh > 0:
                # Energy Δ = Power * Time
                # Power is positive (Discharge) or negative (Charge)?
                # Standard: Negative = Charge key, Positive = Discharge key.
                
                power = state.last_dispatch_kw
                energy_delta_kwh = power * (minutes / 60.0) 
                
                # Check limits
                # If discarding (power > 0): SoC decreases
                # If charging (power < 0): SoC increases (energy_delta is negative, so we subtract it?)
                # Wait, energy_delta is signed.
                # If Power=5kW (Discharge), delta=1.25kWh. SoC should decrease.
                # If Power=-5kW (Charge), delta=-1.25kWh. SoC should increase.
                
                # New Energy = Old Energy - Delta
                current_energy_kwh = (state.soc_percent / 100.0) * state.capacity_kwh
                new_energy_kwh = current_energy_kwh - energy_delta_kwh
                
                # Clamp
                new_energy_kwh = max(0.0, min(state.capacity_kwh, new_energy_kwh))
                
                # Update SoC
                state.soc_percent = (new_energy_kwh / state.capacity_kwh) * 100.0
            
            # 3. PV Generation (Auto-update based on sun)
            if state.asset_type == AssetType.PV:
                # PV doesn't really have "dispatch" typically, but let's say it updates its output
                # This might be pulled by get_telemetry directly from a weather model in a real app
                pass 
