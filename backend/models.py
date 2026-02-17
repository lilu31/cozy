from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

# --- Domain Models ---

class AssetType(str, Enum):
    EV = "EV"
    BATTERY = "BATTERY"
    PV = "PV"
    HEATPUMP = "HEATPUMP"

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    tenants: List["Tenant"] = Relationship(back_populates="user")
    assets: List["Asset"] = Relationship(back_populates="user")

class Tenant(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    address: Optional[str] = None
    grid_connection_capacity_kw: float = 30.0
    
    user: User = Relationship(back_populates="tenants")

class Asset(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    asset_type: AssetType
    display_name: str
    
    # Specs (JSON structure flattened or simplified for MVP)
    capacity_kwh: Optional[float] = None  # For Battery/EV
    max_power_kw: Optional[float] = None  # For all
    
    user: User = Relationship(back_populates="assets")

# --- TimeSeries Models (Hypertables) ---
# Note: For TimescaleDB, we usually partition by time. 
# Primary keys in SQLModel with Timescale can be tricky if not Composite including Time.

class MeterReading(SQLModel, table=True):
    """Telemetry data from assets."""
    timestamp: datetime = Field(primary_key=True)
    asset_id: UUID = Field(primary_key=True, foreign_key="asset.id")
    
    power_kw: float # Negative = Charging/Consuming, Positive = Discharging/Producing
    soc_percent: Optional[float] = None # State of Charge for Batteries/EVs
    energy_kwh: Optional[float] = None # Cumulative counter if available

class MarketPrice(SQLModel, table=True):
    """EPEX SPOT Intraday ID3 or Day-Ahead prices."""
    timestamp: datetime = Field(primary_key=True)
    market_region: str = Field(primary_key=True, default="DE-LU")
    
    price_eur_per_mwh: float

class AssetDispatchSchedule(SQLModel, table=True):
    """Optimization Plan: processed result from our AI."""
    timestamp: datetime = Field(primary_key=True)
    asset_id: UUID = Field(primary_key=True, foreign_key="asset.id")
    
    planned_power_kw: float

class ShadowBillingResult(SQLModel, table=True):
    """Financials: What they paid vs what they would have paid."""
    timestamp: datetime = Field(primary_key=True)
    user_id: UUID = Field(primary_key=True, foreign_key="user.id")
    
    real_cost_eur: float
    benchmark_cost_eur: float
    savings_eur: float

# --- Phase 5: VPP Models ---

class GridDispatchSchedule(SQLModel, table=True):
    """
    The planned Net Grid interaction for a Household.
    This is what the VPP aggregates.
    """
    timestamp: datetime = Field(primary_key=True)
    user_id: UUID = Field(primary_key=True, foreign_key="user.id")
    
    import_kw: float
    export_kw: float
    net_power_kw: float # + = Export, - = Import ? Or specific convention?
    # Let's standardize: Positive = Net Feeding into Grid (Export - Import)
    # Negative = Net Drawing from Grid.

class PortfolioPosition(SQLModel, table=True):
    """
    Aggregated VPP Position.
    """
    timestamp: datetime = Field(primary_key=True)
    region: str = Field(primary_key=True, default="DE-LU")
    
    total_net_power_kw: float # Sum of all GridDispatchSchedules
    secured_power_kw: float = 0.0 # Power already bought/sold on market?
    
class TradeOrder(SQLModel, table=True):
    """
    A trade executed on the market.
    """
    timestamp: datetime = Field(primary_key=True) # Time of Trade Execution (or Delivery Time?)
    # Usually: Delivery Time. Execution Time is metadata.
    # Let's say PK is Delivery Time to match Hypertables pattern easily.
    # But usually a trade covers a period.
    # Let's use Delivery Time as main timestamp.
    
    order_id: str = Field(primary_key=True)
    delivery_timestamp: datetime
    
    side: str # BUY / SELL
    quantity_kwh: float
    price_limit: float
    status: str # FILLED, PENDING
