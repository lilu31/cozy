from datetime import datetime, timedelta
from uuid import uuid4
from sqlmodel import Session, select
from backend.database import engine
from backend.models import PortfolioPosition, TradeOrder
from backend.infrastructure.interfaces import IMarketAdapter
# For MVP, we instantiate the mock directly or use DI. 
# Let's import the Mock directly for now as per "Mock-First" phase.
from backend.infrastructure.mocks.market_mock import MockLumenazaAdapter

class MockTrader:
    def __init__(self):
        self.market = MockLumenazaAdapter()
        self.threshold_kwh = 1.0 # Min delta to trade
    
    def run_trading_loop(self, start_time: datetime = None, horizon_hours: int = 48, region: str = "DE-LU"):
        if start_time is None:
            start_time = datetime.utcnow()
            
        end_time = start_time + timedelta(hours=horizon_hours)
        
        print("Running Trading Loop...")
        
        with Session(engine) as session:
            # 1. Get Portfolio Positions
            positions = session.exec(
                select(PortfolioPosition)
                .where(PortfolioPosition.timestamp >= start_time)
                .where(PortfolioPosition.timestamp <= end_time)
                .where(PortfolioPosition.region == region)
            ).all()
            
            trades_count = 0
            
            for pos in positions:
                # 2. Calculate Secured Power
                # Fetch trades for this delivery timestamp
                trades = session.exec(
                    select(TradeOrder)
                    .where(TradeOrder.delivery_timestamp == pos.timestamp)
                ).all()
                
                secured_net = 0.0
                for t in trades:
                    if t.side == "BUY":
                        secured_net += t.quantity_kwh # Import is + ? 
                        # Wait. Convention: 
                        # Portfolio Net Power: + = Export, - = Import ?
                        # In Orchestrator: net = export - import. So + is Export.
                        # If we are Short (Importing, Negative Net), we need to BUY.
                        # Buying Energy means we are "Recieving" grid power to cover deficit.
                        # So Buy adds to our "Net Position" (making it less negative/more positive balance?).
                        # Usually: Position = Planned_Gen - Planned_Load.
                        # If Position is -10 (Deficit), we Buy 10. Net = -10 + 10 = 0.
                        # So BUY is positive impact on balance.
                        pass
                    elif t.side == "SELL":
                        secured_net -= t.quantity_kwh # Selling reduces our held energy?
                        # If we have +10 Surplus. We Sell 10. Net = +10 - 10 = 0.
                        pass
                
                # Correction: Trade Quantity is usually absolute.
                # Buy 5kWh -> +5. Sell 5kWh -> -5.
                
                # Re-calc Secured from scratch to be safe? 
                # Yes.
                secured_net = sum([t.quantity_kwh if t.side == "BUY" else -t.quantity_kwh for t in trades])
                
                # Update Secured in DB for visibility
                pos.secured_power_kw = secured_net 
                # Note: secured_power_kw is Power (kW) or Energy (kWh)? 
                # Trade is kWh. Position is kW.
                # 15 min block. Energy (kWh) = Power (kW) * 0.25h.
                # Power (kW) = Energy (kWh) / 0.25 = Energy * 4.
                # Let's convert Trade kWh to Average Power kW for the slot.
                secured_power_avg = secured_net * 4.0
                pos.secured_power_kw = secured_power_avg
                session.add(pos)
                
                # 3. Calculate Delta
                target = pos.total_net_power_kw # (+ Export, - Import)
                current = secured_power_avg
                
                delta_kw = target - current
                # Example:
                # Target +10kW (Long/Export). Secured 0. Delta +10. Need to SELL 10kW.
                # Target -10kW (Short/Import). Secured 0. Delta -10. Need to BUY 10kW.
                
                # Convert Delta to Order Quantity (kWh)
                delta_kwh = delta_kw * 0.25
                
                if abs(delta_kwh) > self.threshold_kwh:
                    # Place Order
                    side = "SELL" if delta_kwh > 0 else "BUY"
                    qty = abs(delta_kwh)
                    
                    # Call Market
                    # Assuming Market price is current market price for that slot? 
                    # Mock Adapter place_order takes (quantity, price_limit, side).
                    # We need "Market Price" to set limit? Or Market Order?
                    # Mock just fills everything.
                    limit = 0.0 # Market order
                    
                    print(f"Placing {side} {qty:.2f} kWh for {pos.timestamp} (Delta: {delta_kw:.2f} kW)")
                    order_id = self.market.place_order(qty, limit, side)
                    
                    if order_id:
                        # Record Trade
                        trade = TradeOrder(
                            timestamp=datetime.utcnow(),
                            order_id=order_id or str(uuid4()),
                            delivery_timestamp=pos.timestamp,
                            side=side,
                            quantity_kwh=qty,
                            price_limit=limit,
                            status="FILLED"
                        )
                        session.add(trade)
                        trades_count += 1
            
            session.commit()
            print(f"Trading Loop Complete. Placed {trades_count} orders.")
