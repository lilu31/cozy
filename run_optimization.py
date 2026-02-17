from backend.services.optimization.orchestrator import OptimizationOrchestrator
from backend.database import engine
from backend.models import User, AssetDispatchSchedule
from sqlmodel import Session, select

def verify_optimization():
    print("--- Verifying Phase 4: AI Engine ---")
    
    # 1. Get User
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
        if not user:
            print("User not found.")
            return

    # 2. Run Pipeline
    orchestrator = OptimizationOrchestrator()
    orchestrator.run_pipeline(user.id)
    
    # 3. Check Results
    with Session(engine) as session:
        schedules = session.exec(select(AssetDispatchSchedule)).all()
        count = len(schedules)
        print(f"\nOptimization Result: {count} schedule entries found.")
        
        if count >= 192:
            print("✅ Optimization Successful (48h horizon covering 192 steps).")
            # Print sample
            sample = schedules[0]
            print(f"Sample: {sample.timestamp} | Power: {sample.planned_power_kw} kW")
        else:
            print("⚠️ Optimization might have failed or partial result.")

if __name__ == "__main__":
    verify_optimization()
