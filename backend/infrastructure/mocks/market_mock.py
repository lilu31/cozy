import random
import math
from datetime import datetime
from uuid import uuid4
from ..interfaces import IMarketAdapter

class MockLumenazaAdapter(IMarketAdapter):
    def get_current_price(self, region: str = "DE-LU") -> float:
        """
        Generates a volatile price around a sine wave.
        """
        now = datetime.utcnow()
        seconds = (now - now.replace(hour=0, minute=0, second=0)).total_seconds()
        
        # 24h sine wave
        base_price = 100.0 # EUR/MWh
        amplitude = 50.0
        
        # Peak at 19:00 (approx 68400s), Trough at 04:00 maybe?
        # Simple sine: sin(t)
        val = base_price + amplitude * math.sin(2 * math.pi * seconds / 86400)
        
        # Add volatility (Market noise)
        noise = random.uniform(-15.0, 15.0)
        
        return round(val + noise, 2)

    def place_order(self, quantity_kwh: float, price_limit: float, side: str = "BUY") -> str:
        """
        Simulates placing an order on the EPEX SPOT.
        """
        # In a mock, we fill immediately.
        order_id = str(uuid4())
        print(f"[MOCK MARKET] Order {order_id}: {side} {quantity_kwh}kWh @ {price_limit} EUR/MWh -> FILLED")
        return order_id
