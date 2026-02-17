from sqlmodel import Session
from datetime import datetime, timedelta
import random
from backend.database import engine
from backend.models import MarketPrice

def seed_future_prices():
    print("Seeding future market prices...")
    
    with Session(engine) as session:
        # Start from now floored to hour
        start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        # Seed for next 48 hours
        hours = 48
        
        region = "DE-LU"
        
        for i in range(hours):
            t = start + timedelta(hours=i)
            
            # Simple daily curve pattern
            hour = t.hour
            base_price = 80.0
            
            # Morning peak (8-10)
            if 8 <= hour <= 10:
                price = base_price + random.uniform(20, 50)
            # Evening peak (18-21)
            elif 18 <= hour <= 21:
                price = base_price + random.uniform(30, 60)
            # Night dip (0-5)
            elif 0 <= hour <= 5:
                price = base_price - random.uniform(10, 30)
            # Solar dip (11-15)
            elif 11 <= hour <= 15:
                price = base_price - random.uniform(20, 40)
            else:
                price = base_price + random.uniform(-10, 10)
                
            # Random volatility
            price += random.uniform(-5, 5)
            
            # Check if exists
            existing = session.get(MarketPrice, (t, region))
            if not existing:
                mp = MarketPrice(
                    timestamp=t,
                    market_region=region,
                    price_eur_per_mwh=round(price, 2)
                )
                session.add(mp)
            else:
                existing.price_eur_per_mwh = round(price, 2)
                session.add(existing)
                
        session.commit()
        print(f"Seeded {hours} hours of prices starting from {start}.")

if __name__ == "__main__":
    seed_future_prices()
