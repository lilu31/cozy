from datetime import datetime, timedelta
from typing import List
from sqlmodel import Session, select, func
from backend.database import engine
from backend.models import GridDispatchSchedule, PortfolioPosition

class VPPAggregator:
    def aggregate_portfolio(self, start_time: datetime = None, horizon_hours: int = 48, region: str = "DE-LU"):
        if start_time is None:
            start_time = datetime.utcnow()
        
        # Round to nearest 15 mins
        start_time = start_time.replace(second=0, microsecond=0)
        start_time = start_time - timedelta(minutes=start_time.minute % 15)
        
        end_time = start_time + timedelta(hours=horizon_hours)
        
        print(f"Aggregating Portfolio for {start_time} to {end_time}...")
        
        with Session(engine) as session:
            # 1. Fetch all Grid Schedules in range
            # We want to group by timestamp and SUM(net_power_kw)
            
            # Helper: Get unique timestamps first or use a raw grouping query?
            # SQLModel group_by is a bit verbose, let's try raw pandas or python sum for MVP clarity/safety.
            # Fetching raw rows is fine for small MVP scale.
            
            schedules = session.exec(
                select(GridDispatchSchedule)
                .where(GridDispatchSchedule.timestamp >= start_time)
                .where(GridDispatchSchedule.timestamp <= end_time)
            ).all()
            
            if not schedules:
                print("No schedules found to aggregate.")
                return

            # Group by Timestamp
            agg_map = {}
            for s in schedules:
                ts = s.timestamp
                if ts not in agg_map:
                    agg_map[ts] = 0.0
                agg_map[ts] += s.net_power_kw
            
            # 2. Save Portfolio Positions
            count = 0
            for ts, total_net in agg_map.items():
                # Upsert Logic: Check if exists
                existing = session.get(PortfolioPosition, (ts, region))
                if existing:
                    existing.total_net_power_kw = total_net
                    session.add(existing)
                else:
                    pos = PortfolioPosition(
                        timestamp=ts,
                        region=region,
                        total_net_power_kw=total_net,
                        secured_power_kw=0.0 # Initial
                    )
                    session.add(pos)
                count += 1
            
            session.commit()
            print(f"Aggregated {count} portfolio positions.")
