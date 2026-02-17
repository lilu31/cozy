from sqlmodel import Session, select
from datetime import datetime, timedelta
from backend.database import engine
from backend.models import MarketPrice

def check_prices():
    with Session(engine) as session:
        now = datetime.utcnow()
        end = now + timedelta(hours=24)
        
        print(f"Checking prices between {now} and {end}...")
        
        prices = session.exec(select(MarketPrice).where(
            MarketPrice.timestamp >= now,
            MarketPrice.timestamp <= end
        )).all()
        
        print(f"Found {len(prices)} price entries.")
        if prices:
            print(f"First: {prices[0].timestamp} - {prices[0].price_eur_per_mwh}")
            print(f"Last: {prices[-1].timestamp} - {prices[-1].price_eur_per_mwh}")
        else:
            # Check latest available
            latest = session.exec(select(MarketPrice).order_by(MarketPrice.timestamp.desc())).first()
            if latest:
                print(f"No future data. Latest entry is at: {latest.timestamp}")
            else:
                print("Table is empty.")

if __name__ == "__main__":
    check_prices()
