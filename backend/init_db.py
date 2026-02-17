from sqlmodel import SQLModel, text
from database import engine
import models

def init_db():
    print("Creating tables...")
    SQLModel.metadata.create_all(engine)
    
    print("Converting to Hypertables...")
    with engine.connect() as conn:
        # Enable TimescaleDB extension if not already enabled (might need superuser)
        # conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
        # Using execute inside a transaction block if needed.
        # Note: 'IF NOT EXISTS' in create_hypertable is supported in recent versions or handle exception.
        
        hypertables = [
            "meterreading",
            "marketprice",
            "assetdispatchschedule",
            "shadowbillingresult",
            "griddispatchschedule",
            "portfolioposition",
            "tradeorder"
        ]
        
        for table in hypertables:
            try:
                # migrate_data=True allows converting even if empty, effectively preparing it
                query = text(f"SELECT create_hypertable('{table}', 'timestamp', if_not_exists => TRUE);")
                conn.execute(query)
                print(f" - {table} is a hypertable.")
            except Exception as e:
                print(f"Could not convert {table}: {e}")
        
        conn.commit()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
