from ortools.linear_solver import pywraplp
import pandas as pd
import numpy as np
from typing import Dict, Any, List

class HomeEnergySolver:
    def __init__(self):
        self.solver = pywraplp.Solver.CreateSolver('GLOP')
        self.solver.SetTimeLimit(5000) # 5 seconds max

    def solve(self, 
              horizon: int, 
              prices: List[float], 
              net_loads: List[float], 
              asset_specs: Dict[str, Any],
              initial_soc: float = 0.0) -> pd.DataFrame:
        """
        Solves the MPC problem.
        horizon: number of time steps (e.g., 96 for 24h).
        prices: array of length horizon (Import Price).
        net_loads: array of length horizon (Load - PV). Positive = Deficit.
        asset_specs: {'battery': {'capacity': 10, 'max_power': 5, 'eff': 0.95}}
        """
        if not self.solver:
            return pd.DataFrame()

        # Specs
        bat = asset_specs.get('battery', {})
        BAT_CAP = bat.get('capacity', 10.0)
        BAT_POWER = bat.get('max_power', 5.0)
        BAT_EFF = bat.get('eff', 0.95)
        
        # Variables
        grid_import = {}
        grid_export = {}
        bat_charge = {}
        bat_discharge = {}
        soc = {}
        
        dt = 0.25 # 15 min
        
        infinity = self.solver.infinity()

        for t in range(horizon):
            # Grid
            grid_import[t] = self.solver.NumVar(0, infinity, f'import_{t}')
            grid_export[t] = self.solver.NumVar(0, infinity, f'export_{t}')
            
            # Battery
            bat_charge[t] = self.solver.NumVar(0, BAT_POWER, f'cha_{t}')
            bat_discharge[t] = self.solver.NumVar(0, BAT_POWER, f'dis_{t}')
            soc[t] = self.solver.NumVar(0, BAT_CAP, f'soc_{t}')
            
        # Constraints
        for t in range(horizon):
            # 1. Physics: SoC Evolution
            # SoC_t = SoC_{t-1} + Charge*eff*dt - Discharge/eff*dt
            prev_soc = soc[t-1] if t > 0 else initial_soc
            
            self.solver.Add(
                soc[t] == prev_soc + (bat_charge[t] * BAT_EFF * dt) - (bat_discharge[t] / BAT_EFF * dt)
            )
            
            # 2. Power Balance
            # Import + Discharge + PV = Load + Export + Charge
            # Rearranged: Import - Export = (Load - PV) + Charge - Discharge
            # net_load input is (Load - PV)
            
            self.solver.Add(
                grid_import[t] - grid_export[t] == net_loads[t] + bat_charge[t] - bat_discharge[t]
            )
            
        # Objective: Minimize Cost
        # Cost = Import * Price - Export * Price (assuming Net Metering or similar market price)
        objective = self.solver.Objective()
        for t in range(horizon):
            price = prices[t]
            objective.SetCoefficient(grid_import[t], float(price * dt / 1000)) # Price is /MWh
            objective.SetCoefficient(grid_export[t], float(-price * dt / 1000)) # Revenue
            
        objective.SetMinimization()
        
        # Solve
        status = self.solver.Solve()
        
        results = []
        if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            print(f"Solution Found! Objective: {objective.Value():.2f}")
            for t in range(horizon):
                results.append({
                    'step': t,
                    'import_kw': grid_import[t].solution_value(),
                    'export_kw': grid_export[t].solution_value(),
                    'bat_charge_kw': bat_charge[t].solution_value(),
                    'bat_discharge_kw': bat_discharge[t].solution_value(),
                    'soc_kwh': soc[t].solution_value(),
                    'price': prices[t]
                })
        else:
            print("No solution found.")
            
        return pd.DataFrame(results)
