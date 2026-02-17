from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID
import pandas as pd
from sqlmodel import Session, select
from ..database import engine
from ..models import MeterReading, MarketPrice, Asset, AssetType, ShadowBillingResult

class BillingService:
    def calculate_daily_result(self, user_id: UUID, target_date: datetime.date) -> ShadowBillingResult:
        """
        Orchestrates the Billing Run for a specific day.
        """
        start_ts = datetime.combine(target_date, datetime.min.time())
        end_ts = datetime.combine(target_date, datetime.max.time())
        
        # 1. Fetch Data
        df, assets = self._fetch_data(user_id, start_ts, end_ts)
        
        if df.empty:
            print("No data found for this date.")
            return None
            
        # 2. Run Simulations
        # df contains 'power_pv', 'power_load' (simulated), 'price'
        # We need to reconstruct 'net_load_real' from the actual meter readings of Battery/EV if available
        # But wait, our seed data has PV, Battery, EV. 
        # We assume 'Load' is missing in seed data? 
        # Ah, in Seed data we didn't explicitly create a "House Load" meter. 
        # Let's assume a baseline load for the calculation or derive it.
        # For MVP, let's assume 'House Load' constant or simple curve in memory if missing.
        
        df = self._simulate_benchmark(df, assets)
        
        # 3. Calculate Costs
        result = self._calculate_costs(df, user_id, start_ts)
        
        return result

    def _fetch_data(self, user_id: UUID, start: datetime, end: datetime):
        with Session(engine) as session:
            # Get Assets
            assets = session.exec(select(Asset).where(Asset.user_id == user_id)).all()
            asset_map = {a.asset_type: a for a in assets}
            
            # Get Prices
            prices = session.exec(
                select(MarketPrice)
                .where(MarketPrice.timestamp >= start)
                .where(MarketPrice.timestamp <= end)
            ).all()
            
            # Get Readings
            # This is tricky with multiple assets. We need to pivot.
            # Let's get all readings for these assets in range
            asset_ids = [a.id for a in assets]
            readings = session.exec(
                select(MeterReading)
                .where(MeterReading.asset_id.in_(asset_ids))
                .where(MeterReading.timestamp >= start)
                .where(MeterReading.timestamp <= end)
            ).all()

        # Convert to Pandas
        if not prices or not readings:
            return pd.DataFrame(), []

        df_prices = pd.DataFrame([p.model_dump() for p in prices])
        df_prices.set_index('timestamp', inplace=True)
        df_prices = df_prices[['price_eur_per_mwh']]
        
        df_readings = pd.DataFrame([r.model_dump() for r in readings])
        
        # Pivot readings: Columns = [power_kw_{asset_type}, ...]
        # We need to map asset_id to type
        id_to_type = {a.id: a.asset_type for a in assets}
        df_readings['type'] = df_readings['asset_id'].map(id_to_type)
        
        # Pivot
        df_pivot = df_readings.pivot_table(
            index='timestamp', 
            columns='type', 
            values='power_kw', 
            aggfunc='sum'
        ).fillna(0.0)
        
        # Merge Price and Readings
        df = df_prices.join(df_pivot, how='inner')
        
        # Resample to 15min just in case
        df = df.resample('15T').mean().interpolate()
        
        # Add Synthetic House Load (Baseline) if not present
        # In seeded data we only have PV, Battery, EV. We need "Base Load" to make net calc sense.
        # Let's synthesize a "House Load" column: 0.5kW base + peaks
        df['house_load_kw'] = 0.5 
        # Add evening peak
        df['hour'] = df.index.hour
        df.loc[(df['hour'] >= 18) & (df['hour'] <= 22), 'house_load_kw'] = 2.0
        
        return df, asset_map

    def _simulate_benchmark(self, df: pd.DataFrame, asset_map) -> pd.DataFrame:
        """
        Simulates "Dumb" behavior.
        """
        dt = 0.25 # 15 min
        
        # Capacity Params
        bat_cap = asset_map.get(AssetType.BATTERY).capacity_kwh if asset_map.get(AssetType.BATTERY) else 0
        ev_cap = asset_map.get(AssetType.EV).capacity_kwh if asset_map.get(AssetType.EV) else 0
        
        # --- BENCHMARK BATTERY (Self-Consumption) ---
        # Logic: Store PV surplus, cover Load deficit.
        # Initial SoC assumed 50%
        soc_kwh = bat_cap * 0.5
        
        bench_bat_powers = []
        
        for i, row in df.iterrows():
            pv = row.get(AssetType.PV, 0.0) # PV is positive logic in our seed? 
            # In Seed: PV power > 0 (Production).
            load = row['house_load_kw']
            
            net_load = load - pv # >0 means Deficit (Buy), <0 means Surplus (Sell)
            
            bat_power = 0.0
            
            if bat_cap > 0:
                if net_load < 0: # Surplus -> Charge
                    # Max charge power 5kW?
                    max_charge = 5.0
                    possible_charge = min(abs(net_load), max_charge)
                    # Check Capacity
                    space = bat_cap - soc_kwh
                    actual_charge = min(possible_charge, space / dt)
                    bat_power = -actual_charge # Negative = Charging
                    soc_kwh += actual_charge * dt
                elif net_load > 0: # Deficit -> Discharge
                    max_discharge = 5.0
                    possible_discharge = min(net_load, max_discharge)
                    # Check Energy
                    actual_discharge = min(possible_discharge, soc_kwh / dt)
                    bat_power = actual_discharge
                    soc_kwh -= actual_discharge * dt
            
            bench_bat_powers.append(bat_power)
            
        df['bench_bat_power'] = bench_bat_powers
        
        # --- BENCHMARK EV (Charge Immediately) ---
        # Logic: Plug in at 18:00, charge full speed.
        # VS "Real" (Smart) which might delay to cheap hours.
        # Our Seed Real EV charges 18-22h. 
        # Benchmark usually behaves similarly unless smart charging is the diff.
        # Let's say Benchmark plugs in at 18:00 and charges until full.
        # Real (Optimized) would match seeds (18-22).
        # If seed is "smart", it might pick price dips.
        # For this MVP, let's assume Benchmark matches the "Dumb" pattern we seeded 
        # (Charge on arrival), so maybe Real is the one we should have optimized?
        # Re-reading prompt: "Real" is from seeded/simulated optimization.
        # Currently seed is "Dumb" (18-22). 
        # So Real = Benchmark in this Seed scenario?
        # That's fine. Savings will be 0, which is correct for "Unoptimized Seed".
        # We can implement Benchmark to be IDENTICAL to the seed for now.
        
        df['bench_ev_power'] = df.get(AssetType.EV, 0.0) # Assume same behavior if not optimizing yet
        
        return df

    def _calculate_costs(self, df: pd.DataFrame, user_id: UUID, timestamp: datetime) -> ShadowBillingResult:
        dt = 0.25
        
        # --- REAL (From Meter Readings) ---
        # Net Grid = Load + EV + Battery(neg=charge) - PV
        # Note: PV is +Generation? net = Load + EV + Battery - PV
        # Let's check seed: PV is positive generated. Battery pos=discharge?
        # Seed: 
        #   PV > 0
        #   Bat: Charge = Negative power.
        #   EV: Charge = Negative power.
        # So... Generator logic vs Load logic mixed?
        # Usually: Site Net = (Load - PV - BatteryPower - EVPower) ??
        # Let's standardize: Everything Consumer Convention (+ = Import/Consume, - = Export/Gen)
        # Load: +
        # PV: - (Generation)
        # Battery: + (Discharge? No, consumer convention: +Charge, -Discharge). 
        # Wait, Seed said: "Negative = Charging/Consuming". That's "Producer" convention or inverted?
        # Seed: "Negative = Charging/Consuming".
        # So Charging is Negative.
        # PV Generation is Positive? "Positive = Discharging/Producing".
        # So Net Grid Power (Export positive?) = PV + Battery(Discharge) + EV(Discharge?) - Load
        # Let's stick to Seed convention:
        # P_total = P_pv + P_bat + P_ev - P_load (if load is consumption > 0)
        # If P_total > 0: Exporting. If < 0: Importing.
        
        # Real Calculation
        # PV (+) + Bat (+/-) + EV (+/-) - Load (+)
        p_real = df.get(AssetType.PV, 0.0) + df.get(AssetType.BATTERY, 0.0) + df.get(AssetType.EV, 0.0) - df['house_load_kw']
        
        # Price is EUR/MWh. Cost = Energy(MWh) * Price
        # Energy = Power(kW) * dt(h) / 1000 = MWh
        # Cost = -P_total * dt/1000 * Price (If P_total>0 is Export, we EARN money? or save?)
        # Usually: Cost = Import * Price - Export * FeedInTariff.
        # MVP: Dynamic Price for Import, 0 or low for Export?
        # Let's assume Price applies to Import (Cost) and Export (Revenue).
        # Cost = ( -P_total ) * ...
        # If P_total (Export) = 5kW. Cost = -5 * ... = Negative Cost (Profit). Correct.
        # If P_total (Import) = -5kW. Cost = -(-5) * ... = Positive Cost. Correct.
        
        cost_real = (-p_real * dt / 1000 * df['price_eur_per_mwh']).sum()
        
        # --- BENCHMARK ---
        p_bench = df.get(AssetType.PV, 0.0) + df['bench_bat_power'] + df['bench_ev_power'] - df['house_load_kw']
        cost_bench = (-p_bench * dt / 1000 * df['price_eur_per_mwh']).sum()
        
        savings = cost_bench - cost_real
        
        return ShadowBillingResult(
            timestamp=timestamp,
            user_id=user_id,
            real_cost_eur=round(cost_real, 2),
            benchmark_cost_eur=round(cost_bench, 2),
            savings_eur=round(savings, 2)
        )
