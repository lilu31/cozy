from datetime import datetime
from sqlmodel import Session, select
from backend.database import engine
from backend.models import User, PortfolioPosition, TradeOrder
from backend.services.optimization.orchestrator import OptimizationOrchestrator
from backend.services.vpp.aggregator import VPPAggregator
from backend.services.vpp.trader import MockTrader

def verify_vpp():
    print("--- Verifying Phase 5: VPP Engine ---")
    
    # 1. Ensure Optimization Data exists for "Now"
    # We'll re-run orchestrator briefly to be sure.
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
    
    if not user:
        print("User missing.")
        return

    print("1. Running Optimization (to generate households plans)...")
    orch = OptimizationOrchestrator()
    orch.run_pipeline(user.id)
    
    # 2. Run Aggregator
    print("\n2. Running Aggregator...")
    agg = VPPAggregator()
    agg.aggregate_portfolio(horizon_hours=24) # Just 24h
    
    # 3. Run Trader (Pass 1: Detect Open Positions)
    print("\n3. Running Trader (Pass 1 - Place Orders)...")
    trader = MockTrader()
    trader.run_trading_loop(horizon_hours=24)
    
    # 4. Run Trader (Pass 2 - Update Secured Status)
    # The first run places orders.
    # The second run (simulation of next loop) should see them as secured.
    print("\n4. Running Trader (Pass 2 - Verify Secured)...")
    trader.run_trading_loop(horizon_hours=24)
    
    # 5. Check DB
    with Session(engine) as session:
        positions = session.exec(select(PortfolioPosition).limit(5)).all()
        trades = session.exec(select(TradeOrder).limit(5)).all()
        
        print(f"\n--- Results ---")
        print(f"Portfolio Positions: {len(positions)} (Shown 5)")
        for p in positions:
            print(f" - {p.timestamp} | Target: {p.total_net_power_kw:.2f} kW | Secured: {p.secured_power_kw:.2f} kW")
            
        print(f"Trades: {len(trades)} (Shown 5)")
        for t in trades:
            print(f" - {t.order_id} | {t.side} {t.quantity_kwh:.2f} kWh | Del: {t.delivery_timestamp}")
            
        if len(trades) > 0:
            print("✅ VPP Verification Successful: Trades were generated.")
        else:
            print("⚠️ No trades generated. Maybe Delta was too small?")

if __name__ == "__main__":
    verify_vpp()
