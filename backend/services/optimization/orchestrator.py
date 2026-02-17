from datetime import datetime
from uuid import UUID
import random
import pandas as pd
from sqlmodel import Session, select
from backend.database import engine
from backend.models import MeterReading, MarketPrice, Asset, AssetType, AssetDispatchSchedule, GridDispatchSchedule
from .forecasting import ForecastingService
from .solver import HomeEnergySolver

class OptimizationOrchestrator:
    def __init__(self):
        self.forecaster = ForecastingService()
        self.solver = HomeEnergySolver()

    def run_pipeline(self, user_id: UUID):
        print(f"Starting Optimization Pipeline for User {user_id}...")
        
        # 2. Prepare Optimization Horizon
        # We want to optimize for [Now, Now + 48h]
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        horizon_steps = 192 # 15-min intervals for 48h? 48*4 = 192.
        
        # Check if we have prices for this horizon
        with Session(engine) as session:
            # We need 48h of prices.
            # Convert to Pandas Series.
            
            future_prices = session.exec(
                select(MarketPrice)
                .where(MarketPrice.timestamp >= now)
                .order_by(MarketPrice.timestamp.asc())
                .limit(48) # hourly prices
            ).all()
            
            price_forecast = pd.Series()
            
            if len(future_prices) >= 48:
                print("Using existing Future Market Prices for optimization...")
                # Resample hourly prices to 15-min
                # Create DataFrame
                df_future = pd.DataFrame([p.model_dump() for p in future_prices]).set_index('timestamp')
                # Resample to 15T and ffill
                price_forecast = df_future['price_eur_per_mwh'].resample('15T').ffill().reindex(
                    pd.date_range(start=now, periods=horizon_steps, freq='15T'), method='ffill'
                )
            else:
                print("Future prices missing, fallback to forecasting...")
                # Fallback to old logic (fetch history, forecast)
                # ... (omitted for brevity, MVP assumes seeded future)
                return
                
            # 3. Forecast/PV Logic (Aligned to price_forecast index)
            # PV History
            assets = session.exec(select(Asset).where(Asset.user_id == user_id)).all()
            pv_asset = next((a for a in assets if a.asset_type == AssetType.PV), None)
            pv_forecast = pd.Series([0.0]*horizon_steps, index=price_forecast.index) # Default 0
            
            if pv_asset:
                # Deterministic Solar Curve for MVP Visualization
                # Max power approx 5kW
                print("Generating Deterministic Solar Forecast...")
                pv_values = []
                for ts in price_forecast.index:
                    h = ts.hour + (ts.minute / 60.0)
                    # Solar window: 06:00 to 20:00
                    # Peak at 13:00
                    val = 0.0
                    if 6 <= h <= 20:
                         # Normalized sine wave
                         # (h - 6) / 14 * pi
                         import math
                         angle = (h - 6) / 14 * math.pi
                         val = 5.0 * math.sin(angle)
                         # Add noise
                         val += random.uniform(-0.2, 0.2)
                    pv_values.append(max(0.0, val))
                
                pv_forecast = pd.Series(pv_values, index=price_forecast.index)
            
            # Synthetic Load Forecast (Aligned)
            future_index = price_forecast.index
            load_forecast = []
            for ts in future_index:
                h = ts.hour
                val = 0.5 # Base
                if 7 <= h <= 9 or 18 <= h <= 21:
                    val = 2.0
                load_forecast.append(val)
            load_forecast = pd.Series(load_forecast, index=future_index)
            
            # 4. Net Load
            # Net Load = Load - PV
            net_load_forecast = load_forecast - pv_forecast.values
            
            # 5. Solve
            print("Solving Optimization Problem...")
            bat_asset = next((a for a in assets if a.asset_type == AssetType.BATTERY), None)
            bat_specs = {}
            if bat_asset:
                bat_specs = {
                    'capacity': bat_asset.capacity_kwh, 
                    'max_power': bat_asset.max_power_kw, 
                    'eff': 0.95
                }
            
            solution = self.solver.solve(
                horizon=192,
                prices=price_forecast.values,
                net_loads=net_load_forecast.values,
                asset_specs={'battery': bat_specs},
                initial_soc=5.0 # Assume 50% start
            )
            
            # 6. Save Schedule
            if not solution.empty and bat_asset:
                print("Saving Schedule to DB...")
                for i, row in solution.iterrows():
                    ts = price_forecast.index[int(row['step'])]
                    
                    # 1. Save Battery Schedule
                    bat_power = float(row['bat_discharge_kw'] - row['bat_charge_kw'])
                    
                    schedule_bat = AssetDispatchSchedule(
                        timestamp=ts,
                        asset_id=bat_asset.id,
                        planned_power_kw=bat_power
                    )
                    session.merge(schedule_bat)
                    
                    # 2. Save PV Schedule (Forecast)
                    if pv_asset:
                        # Ensure we align with step i
                        # pv_forecast is a Series aligned with price_forecast
                        pv_val = max(0.0, float(pv_forecast.iloc[i])) # Clamp to 0
                        schedule_pv = AssetDispatchSchedule(
                            timestamp=ts,
                            asset_id=pv_asset.id,
                            planned_power_kw=pv_val # Positive = Production
                        )
                        session.merge(schedule_pv)

                    # 3. Save EV Schedule (Mock Smart Charging)
                    # Heuristic: Charge 7kW if Price < 50 EUR (Cheap) and hour is 22:00-06:00
                    # This simulates a "Smart Charger" responding to price or time
                    ev_asset = next((a for a in assets if a.asset_type == AssetType.EV), None)
                    if ev_asset:
                        ev_power = 0.0
                        price_now = float(price_forecast.iloc[i])
                        h = ts.hour
                        # Simple Logic: Charge at night
                        if (22 <= h or h <= 5):
                            ev_power = -11.0 # 11kW Charging (Negative = Load)
                            
                        schedule_ev = AssetDispatchSchedule(
                            timestamp=ts,
                            asset_id=ev_asset.id,
                            planned_power_kw=ev_power
                        )
                        session.merge(schedule_ev)
                    
                    # 4. Save Grid Schedule
                    # Net Power = Export - Import
                    import_kw = float(row['import_kw'])
                    export_kw = float(row['export_kw'])
                    net_power = export_kw - import_kw
                    
                    grid_schedule = GridDispatchSchedule(
                        timestamp=ts,
                        user_id=user_id,
                        import_kw=import_kw,
                        export_kw=export_kw,
                        net_power_kw=net_power
                    )
                    session.merge(grid_schedule)
                session.commit()
                print("Optimization Complete.")

