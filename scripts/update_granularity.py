from datetime import datetime, timedelta
import random
from sqlmodel import Session, select
from backend.database import engine
from backend.models import User, MarketPrice, AssetDispatchSchedule, GridDispatchSchedule
from backend.services.optimization.orchestrator import OptimizationOrchestrator

def update_granularity():
    with Session(engine) as session:
        print("Starting Granularity Update...")
        
        # 1. Get Test User
        user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
        if not user:
            print("User not found!")
            return

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        
        # 2. Delete Future Data (Prices & Schedules)
        print(f"Deleting future data from {now}...")
        
        # Prices
        prices = session.exec(select(MarketPrice).where(MarketPrice.timestamp >= now)).all()
        for p in prices:
            session.delete(p)
            
        # Schedules (Asset & Grid)
        schedules_a = session.exec(select(AssetDispatchSchedule).where(AssetDispatchSchedule.timestamp >= now)).all()
        for s in schedules_a:
            session.delete(s)
            
        schedules_g = session.exec(select(GridDispatchSchedule).where(GridDispatchSchedule.timestamp >= now)).all()
        for s in schedules_g:
            session.delete(s)
            
        session.commit()
        print("Future data cleared.")
        
        # 3. Seed Hourly Prices for 48h
        print("Seeding Hourly prices...")
        horizon_steps = 48 # 48 hours
        new_prices = []
        
        curr = now
        for _ in range(horizon_steps):
            # Price Logic: Peak at 8am and 7pm
            hour = curr.hour
            base_price = 250.0 
            
            # Add some randomness/volatility for "realism"
            noise = random.uniform(-10, 10)
            
            if 7 <= hour <= 9 or 17 <= hour <= 20:
                price_val = base_price + random.uniform(50, 150)
            elif 11 <= hour <= 15: # Solar dip
                price_val = base_price - random.uniform(50, 150)
            else:
                price_val = base_price + random.uniform(-20, 20)
            
            # Smooth it out locally so it's not jagged every 15 mins? 
            # Actually jagged is fine, markets are volatile.
            
            new_prices.append(MarketPrice(
                timestamp=curr, 
                price_eur_per_mwh=max(0, price_val + noise)
            ))
            curr += timedelta(hours=1)
            
        session.add_all(new_prices)
        session.commit()
        print(f"Seeded {len(new_prices)} price records (1-hour resolution).")
        
        # 4. Run Optimization to Generate 15-min Schedules
        print("Triggering Re-Optimization...")
        orchestrator = OptimizationOrchestrator()
        orchestrator.run_pipeline(user.id)
        print("Update Complete!")

if __name__ == "__main__":
    update_granularity()
