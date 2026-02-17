from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class SavingsSummary(BaseModel):
    real_cost_eur: float
    benchmark_cost_eur: float
    savings_eur: float
    savings_percent: float

class CurrentStateResponse(BaseModel):
    solar_power_kw: float
    grid_power_kw: float
    battery_power_kw: float
    ev_power_kw: float = 0.0 # Added EV Power
    battery_soc: float
    home_load_kw: float

class ChartPoint(BaseModel):
    timestamp: datetime
    price: float
    solar_kw: Optional[float] = 0.0
    load_kw: Optional[float] = 0.0
    battery_kw: Optional[float] = 0.0
    ev_kw: Optional[float] = 0.0 # Added EV
    grid_kw: Optional[float] = 0.0
    soc: Optional[float] = 0.0

class DashboardResponse(BaseModel):
    summary: SavingsSummary
    month_savings_eur: float = 0.0 # Added Monthly Savings
    current: CurrentStateResponse
    history: List[ChartPoint]
    forecast: List[ChartPoint]

class AssetResponse(BaseModel):
    id: UUID
    display_name: str
    asset_type: str
    capacity_kwh: Optional[float]
    max_power_kw: Optional[float]
    current_power_kw: Optional[float]
    current_soc: Optional[float]

class AssetPreferenceUpdate(BaseModel):
    target_soc: float

class DailyReportResponse(BaseModel):
    date: datetime
    summary: SavingsSummary
    optimized_series: List[ChartPoint]
    benchmark_series: List[ChartPoint]
