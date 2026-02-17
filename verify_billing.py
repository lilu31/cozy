from datetime import datetime, timedelta
from sqlmodel import Session, select
from backend.database import engine
from backend.models import User
from backend.services.billing import BillingService

def verify_billing():
    # 1. Get User
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
        if not user:
            print("User test@cozy.io not found! Did you seed?")
            return

    # 2. Run Billing for Yesterday
    target_date = datetime.utcnow().date() - timedelta(days=1)
    print(f"Running Shadow Billing for {target_date}...")
    
    service = BillingService()
    result = service.calculate_daily_result(user.id, target_date)
    
    if result:
        print("\n--- Shadow Bill Result ---")
        print(f"Real Cost:      {result.real_cost_eur} EUR")
        print(f"Benchmark Cost: {result.benchmark_cost_eur} EUR")
        print(f"Savings:        {result.savings_eur} EUR")
        
        if result.savings_eur != 0:
            print("\n✅ Valid Result: Savings calculated.")
        else:
            print("\n⚠️  Result: Zero savings (Expected if Real matches Benchmark exactly).")
            
    else:
        print("No result generated (maybe no data?).")

if __name__ == "__main__":
    verify_billing()
