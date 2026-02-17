from fastapi import APIRouter, Depends
from backend.simulation import get_simulated_load_kw

from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, select
from backend.database import engine
from backend.models import User, Asset, AssetType, MeterReading, ShadowBillingResult, MarketPrice, AssetDispatchSchedule, GridDispatchSchedule
from backend.api.schemas import DashboardResponse, SavingsSummary, CurrentStateResponse, ChartPoint, DailyReportResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

from backend.services.tenancy.auth import get_current_context

# --- Helper Logic ---
def _calculate_savings_period(session: Session, start: datetime, end: datetime) -> Dict[str, Any]:
    """
    Calculates Real vs Benchmark savings for a given period.
    Returns dictionary with 'summary', 'optimized_series', 'benchmark_series'.
    """
    # 1. Fetch Readings
    readings = session.exec(select(MeterReading).where(
        MeterReading.timestamp >= start,
        MeterReading.timestamp < end
    ).order_by(MeterReading.timestamp)).all()
    
    # 2. Fetch Prices
    prices = session.exec(select(MarketPrice).where(
        MarketPrice.timestamp >= start,
        MarketPrice.timestamp < end
    )).all()
    price_map = {p.timestamp: p.price_eur_per_mwh / 1000.0 for p in prices} # EUR/kWh
    
    # 3. Process Data Grouped by Timestamp
    data_map = {}
    for r in readings:
        if r.timestamp not in data_map:
            data_map[r.timestamp] = {'pv': 0, 'bat': 0, 'ev': 0}
            
        asset = session.get(Asset, r.asset_id)
        if not asset: continue
        
        if asset.asset_type == AssetType.PV:
            data_map[r.timestamp]['pv'] += r.power_kw
        elif asset.asset_type == AssetType.BATTERY:
            data_map[r.timestamp]['bat'] += r.power_kw
        elif asset.asset_type == AssetType.EV:
            data_map[r.timestamp]['ev'] += r.power_kw
            
    # 4. Construct Series
    optimized_points = []
    benchmark_points = []
    
    total_real_cost = 0.0
    total_benchmark_cost = 0.0
    
    total_bat_inventory_change_kwh = 0.0
    
    sorted_ts = sorted(list(data_map.keys()))
    
    for ts in sorted_ts:
        vals = data_map[ts]
        pv = vals['pv']
        bat = vals['bat'] # > 0 Discharge (Supply), < 0 Charge (Load)
        ev = vals['ev']
        load = get_simulated_load_kw(ts) # Dynamic realistic load
        price = price_map.get(ts, 0.30) # Default 30ct
        
        # --- REAL / OPTIMIZED ---
        # Grid = Load - PV - Bat - EV
        real_grid = load - pv - bat - ev
        
        optimized_points.append(ChartPoint(
            timestamp=ts,
            price=price,
            grid_kw=real_grid,
            solar_kw=pv,
            battery_kw=bat,
            ev_kw=ev,
            load_kw=load
        ))
        
        # Cost
        total_real_cost += (real_grid * 0.25 * price)
        
        # Track Inventory (Charge increases inventory)
        # bat > 0 is discharge (removes from inventory)
        # bat < 0 is charge (adds to inventory)
        # Change = -bat * 0.25
        total_bat_inventory_change_kwh += (-bat * 0.25)
        
        # --- BENCHMARK (No Smart Tech) ---
        bench_grid = load - pv - ev 
        
        benchmark_points.append(ChartPoint(
            timestamp=ts,
            price=price,
            grid_kw=bench_grid,
            solar_kw=pv,
            battery_kw=0, 
            ev_kw=ev,
            load_kw=load
        ))
        
        total_benchmark_cost += (bench_grid * 0.25 * price)
        
    # Valid prices for valuation
    valid_prices = [price_map[ts] for ts in sorted_ts if ts in price_map]
    avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0.30
    
    # Value Inventory Change: 
    # Apply Efficiency Factor (0.9) to reflect that stored energy is worth less than grid energy 
    # due to round-trip losses. This prevents "Paper Losses" when discharging.
    inventory_value_eur = total_bat_inventory_change_kwh * avg_price * 0.9
    
    cash_flow_savings = total_benchmark_cost - total_real_cost
    total_economic_savings = cash_flow_savings + inventory_value_eur
        
    summary = SavingsSummary(
        real_cost_eur=total_real_cost,
        benchmark_cost_eur=total_benchmark_cost,
        savings_eur=total_economic_savings, # Now includes inventory value
        savings_percent=0 
    )
    
    return {
        "summary": summary,
        "optimized_series": optimized_points,
        "benchmark_series": benchmark_points
    }

@router.get("/summary", response_model=DashboardResponse)
def get_dashboard_summary(user: User = Depends(get_current_context)):
    """
    Returns main dashboard data.
    Savings now covers the last 48 hours ("Optimization Horizon") to avoid negative cash flow artifacts.
    """
    with Session(engine) as session:
        if not user: return {}

        # 1. Savings (Last 48h)
        now = datetime.utcnow()
        now_floored = now.replace(minute=0, second=0, microsecond=0)
        
        # A. Last 48h
        start_48h = now_floored - timedelta(hours=48)
        res_48h = _calculate_savings_period(session, start_48h, now_floored)
        savings_data_48h = res_48h['summary']
        
        # B. Current Month
        start_month = now_floored.replace(day=1, hour=0, minute=0, second=0)
        # If today is 1st, look back 1 month? No, "Current Month" usually means "Oct 1 - Now". 
        # If it's empty start, it returns 0.
        res_month = _calculate_savings_period(session, start_month, now_floored)
        savings_month_eur = res_month['summary'].savings_eur
        
        # 3. Current State (Latest Meter Reading)
        # We need to fetch the reading closest to 'now' to avoid future data artifacts
        # or just use the latest available if we trust the seed script nicely.
        # But properly: 'now_floored' (which is this hour/minute).
        
        assets = session.exec(select(Asset).where(Asset.user_id == user.id)).all()
        
        # Calculate Real Load
        current_load = get_simulated_load_kw(now_floored)
        
        current_state = CurrentStateResponse(
            solar_power_kw=0, 
            grid_power_kw=0, 
            battery_power_kw=0, 
            battery_soc=0, 
            home_load_kw=current_load,
            ev_power_kw=0
        )
        
        # Helper to get reading at current time (approx)
        def get_current_reading(asset_id, field='power_kw'):
            # Look for reading at current timestamp
            r = session.exec(select(MeterReading).where(
                MeterReading.asset_id == asset_id,
                MeterReading.timestamp == now_floored
            )).first()
            if not r:
                # Fallback: Latest reading before now
                r = session.exec(select(MeterReading).where(
                    MeterReading.asset_id == asset_id,
                    MeterReading.timestamp <= now_floored
                ).order_by(MeterReading.timestamp.desc())).first()
            return getattr(r, field) if r else 0.0

        for a in assets:
            power = get_current_reading(a.id)
            if a.asset_type == AssetType.PV:
                current_state.solar_power_kw = power
            elif a.asset_type == AssetType.BATTERY:
                current_state.battery_power_kw = power
                current_state.battery_soc = get_current_reading(a.id, 'soc_percent')
            elif a.asset_type == AssetType.EV:
                current_state.ev_power_kw = power
        
        # Calculate Grid (Net Import/Export)
        # Grid = Load - Generation - Discharge + Charge
        # Grid = Load - PV - Battery (Pos=Discharge) - EV (Neg=Charge? No, usually Neg=Charge)
        # Convention:
        # PV > 0 (Production)
        # Battery > 0 (Discharge/Production), < 0 (Charge/Load)
        # EV < 0 (Charge/Load)
        # Load > 0 (Consumption)
        
        # Net Load = Load - PV - Battery - EV
        # If > 0: Import (Grid Positive)
        # If < 0: Export (Grid Negative)
        
        # Wait, check dashboard logic convention.
        # _calculate_savings_period: real_grid = load - pv - bat - ev
        # This implies:
        # load=5, pv=2, bat=0, ev=0 => grid = 3 (Import). Correct.
        # load=1, pv=5, bat=0, ev=0 => grid = -4 (Export). Correct.
        
        current_state.grid_power_kw = (
            current_state.home_load_kw 
            - current_state.solar_power_kw 
            - current_state.battery_power_kw 
            - current_state.ev_power_kw
        )
        
        # 4. Forecast (Next 24h)
        end_forecast = now_floored + timedelta(hours=24)
        
        # Fetch Prices
        prices = session.exec(select(MarketPrice).where(
            MarketPrice.timestamp >= now_floored, 
            MarketPrice.timestamp <= end_forecast
        ).order_by(MarketPrice.timestamp)).all()
        price_map = {p.timestamp: p.price_eur_per_mwh / 1000.0 for p in prices}
        
        # Fetch Schedules
        user_asset_ids = [a.id for a in assets]
        schedules = session.exec(select(AssetDispatchSchedule).where(
            AssetDispatchSchedule.timestamp >= now_floored,
            AssetDispatchSchedule.timestamp <= end_forecast,
            AssetDispatchSchedule.asset_id.in_(user_asset_ids)
        )).all()
        
        # Aggregate Forecast
        solar_map = {t: 0.0 for t in price_map.keys()}
        battery_map = {t: 0.0 for t in price_map.keys()}
        ev_map = {t: 0.0 for t in price_map.keys()}
        
        asset_type_map = {a.id: a.asset_type for a in assets}

        for s in schedules:
            t = s.timestamp
            if t not in price_map: continue
            atype = asset_type_map.get(s.asset_id)
            power = s.planned_power_kw
            if atype == AssetType.PV: solar_map[t] += power
            elif atype == AssetType.BATTERY: battery_map[t] += power
            elif atype == AssetType.EV: ev_map[t] += power
            
        forecast_points = []
        for t in sorted(list(price_map.keys())):
            s_pw = solar_map.get(t, 0.0)
            b_pw = battery_map.get(t, 0.0)
            e_pw = ev_map.get(t, 0.0)
            base_load = get_simulated_load_kw(t) 
            g_pw = base_load - s_pw - b_pw - e_pw
            
            forecast_points.append(ChartPoint(
                timestamp=t,
                price=price_map.get(t, 0.0),
                grid_kw=g_pw,
                solar_kw=s_pw,
                battery_kw=b_pw,
                ev_kw=e_pw,
                load_kw=base_load
            ))
        
        return DashboardResponse(
            summary=savings_data_48h,
            month_savings_eur=savings_month_eur,
            current=current_state,
            history=[],
            forecast=forecast_points
        )

@router.get("/report/daily", response_model=DailyReportResponse)
def get_daily_report(date_str: str = "48h", user: User = Depends(get_current_context)):
    """
    Returns detailed 15-min series for Real vs Benchmark.
    Defaults to last 48h window to match Dashboard Summary.
    """
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    # Force 48h window for now as per user request
    start = now - timedelta(hours=48)
    end = now
    
    with Session(engine) as session:
        result = _calculate_savings_period(session, start, end)
        
        return DailyReportResponse(
            date=start, # Returns start of window
            summary=result['summary'],
            optimized_series=result['optimized_series'],
            benchmark_series=result['benchmark_series']
        )
