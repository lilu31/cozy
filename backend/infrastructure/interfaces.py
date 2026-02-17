from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class IAssetAdapter(ABC):
    @abstractmethod
    def get_telemetry(self, asset_id: UUID) -> Dict[str, Any]:
        """
        Retrieve current telemetry for the asset.
        Returns a dict that can be mapped to a MeterReading (e.g., {'power_kw': -5.0, 'soc_percent': 50.0}).
        """
        pass
    
    @abstractmethod
    def dispatch(self, asset_id: UUID, power_kw: float) -> bool:
        """
        Send a control command to the asset (e.g., Set Charging Rate).
        Returns True if command acknowledged.
        """
        pass

class IMarketAdapter(ABC):
    @abstractmethod
    def get_current_price(self, region: str = "DE-LU") -> float:
        """
        Get current market price in EUR/MWh.
        """
        pass
    
    @abstractmethod
    def place_order(self, quantity_kwh: float, price_limit: float, side: str = "BUY") -> str:
        """
        Place a trade on the intraday market.
        Returns order_id.
        """
        pass
