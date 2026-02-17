from fastapi import APIRouter, Depends
from typing import List
from sqlmodel import Session, select
from backend.database import engine
from backend.models import Asset, MeterReading
from backend.api.schemas import AssetResponse, AssetPreferenceUpdate

router = APIRouter(prefix="/assets", tags=["Assets"])

from backend.services.tenancy.auth import get_current_context
from backend.models import User

@router.get("/", response_model=List[AssetResponse])
def list_assets(user: User = Depends(get_current_context)):
    with Session(engine) as session:
        # Filter by Tenant/User
        assets = session.exec(select(Asset).where(Asset.user_id == user.id)).all()
        response = []
        for a in assets:
            # Get latest state
            reading = session.exec(select(MeterReading).where(MeterReading.asset_id == a.id).order_by(MeterReading.timestamp.desc())).first()
            
            response.append(AssetResponse(
                id=a.id,
                display_name=a.display_name,
                asset_type=a.asset_type.value,
                capacity_kwh=a.capacity_kwh,
                max_power_kw=a.max_power_kw,
                current_power_kw=reading.power_kw if reading else 0.0,
                current_soc=reading.soc_percent if reading else None
            ))
        return response

@router.post("/{id}/preferences")
def update_asset_preferences(id: str, prefs: AssetPreferenceUpdate):
    # MVP: Log it, maybe save to a new 'AssetPreferences' table later.
    print(f"Update Asset {id} prefs: {prefs}")
    return {"status": "updated"}
