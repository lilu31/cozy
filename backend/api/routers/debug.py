from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from sqlmodel import Session, select
from backend.database import engine
from backend.models import User, MeterReading, Asset, AssetType
from backend.infrastructure.mocks.asset_mock import MockAssetAdapter
from backend.services.optimization.orchestrator import OptimizationOrchestrator
from backend.services.vpp.aggregator import VPPAggregator
from backend.services.vpp.trader import MockTrader

router = APIRouter(prefix="/debug", tags=["Debug"])

from backend.services.tenancy.auth import get_current_context

@router.post("/advance-time")
def advance_time(minutes: int = 15, user: User = Depends(get_current_context)):
    """
    Simulates time passing.
    1. Update Mock Physics (Advance State).
    2. Append new Meter Readings to DB (Time Travel).
    3. Trigger Optimization (Re-plan).
    4. Trigger VPP (Re-aggregate & Trade).
    """
    print(f"--- TIME TRAVEL: Advancing {minutes} minutes ---")
    
    with Session(engine) as session:
        # User is provided by Auth Context
            
        assets = session.exec(select(Asset).where(Asset.user_id == user.id)).all()
        
        # 1. Determine "New Now"
        # Find latest reading to know where we are
        last_reading = session.exec(select(MeterReading).order_by(MeterReading.timestamp.desc())).first()
        if not last_reading:
            current_sim_time = datetime.utcnow()
        else:
            current_sim_time = last_reading.timestamp
            
        next_time = current_sim_time + timedelta(minutes=minutes)
        print(f"Moving from {current_sim_time} to {next_time}")
        
        # 2. Physics Step
        mock = MockAssetAdapter() # This uses in-memory state.
        # Problem: In-memory state is lost between API calls if server restarts loops?
        # Actually, MockAssetAdapter creates state per instance? 
        # Check implementation: `_states = {}` is class-level? No, instance level.
        # If we re-instantiate MockAssetAdapter every request, state is reset!
        # MVP Hack: Load state from DB (latest reading) every time, OR make MockAdapter Singleton.
        # Let's do "Load from Last Reading" approach for robustness.
        
        new_readings = []
        
        for asset in assets:
            # Rehydrate Mock State from last reading
            last_r = session.exec(select(MeterReading).where(MeterReading.asset_id == asset.id).order_by(MeterReading.timestamp.desc())).first()
            if last_r and asset.asset_type in [AssetType.BATTERY, AssetType.EV]:
                state = mock._get_or_create_state(asset.id, asset.asset_type, asset.capacity_kwh)
                if last_r.soc_percent is not None:
                    state.soc_percent = last_r.soc_percent
            
            # Simulate Step
            # Mock expects a Dispatch Command? "physics_step" just updates SoC based on previous dispatch?
            # Or we instruct it what happened.
            # Simplified: Random walk or continue last dispatch?
            # Let's assume 0 dispatch (Idle) unless we read the Schedule!
            
            # Read Schedule for this interval
            # We look for a schedule at 'next_time' (the time we are moving into)
            # OR 'current_sim_time'? Dispatch is set for the upcoming interval. 
            # Dispatch at T applies to T -> T+15. 
            # So we check schedule for `current_sim_time`.
            from backend.models import AssetDispatchSchedule
            
            schedule = session.exec(
                select(AssetDispatchSchedule)
                .where(AssetDispatchSchedule.asset_id == asset.id)
                .where(AssetDispatchSchedule.timestamp == current_sim_time)
            ).first()
            
            dispatch_kw = schedule.planned_power_kw if schedule else 0.0
            
            # Update Mock
            mock.dispatch(asset.id, dispatch_kw) # Sets target
            mock.simulate_physics_step(minutes) # Updates SoC
            
            telemetry = mock.get_telemetry(asset.id)
            
            # Create Reading
            reading = MeterReading(
                timestamp=next_time,
                asset_id=asset.id,
                power_kw=telemetry['power_kw'],
                soc_percent=telemetry.get('soc_percent'),
                energy_kwh=0 # TODO
            )
            session.add(reading)
            new_readings.append(reading)
            
        session.commit()
        
        # 3. Trigger Optimization
        orchestrator = OptimizationOrchestrator()
        orchestrator.run_pipeline(user.id)
        
        # 4. Trigger VPP
        agg = VPPAggregator()
        agg.aggregate_portfolio(start_time=next_time - timedelta(hours=1), horizon_hours=24)
        
        trader = MockTrader()
        trader.run_trading_loop(start_time=next_time - timedelta(hours=1), horizon_hours=24)
        
    return {"status": "ok", "new_time": next_time, "readings": len(new_readings)}
