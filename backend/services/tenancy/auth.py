from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlmodel import Session, select
from backend.database import engine
from backend.models import User

# Schemes
api_key_scheme = APIKeyHeader(name="X-API-KEY", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

def get_session():
    with Session(engine) as session:
        yield session

def get_current_context(
    api_key: Optional[str] = Security(api_key_scheme),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    session: Session = Depends(get_session)
) -> User:
    """
    Resolves the current User/Tenant context from Auth Headers.
    Success: Returns a valid User object.
    Failure: Raises 401 Unauthorized.
    """
    
    # 1. Debug/Dev Mode: If "DEBUG_USER" key is passed (or no auth in strict dev env?)
    # For MVP, let's allow a special API Key "COZY_DEV_KEY" to map to the seed user.
    if api_key == "COZY_DEV_KEY":
        user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
        if user:
            return user
            
    # 2. Bearer Token (JWT)
    # In real app: Decode JWT, verify signature, extract sub (user_id).
    # For Mock-First MVP: Accept ANY non-empty Bearer token and map to seed user 
    # (simulating a valid login).
    if bearer and bearer.credentials:
        # Check if it looks like a token
        if len(bearer.credentials) > 5:
             user = session.exec(select(User).where(User.email == "test@cozy.io")).first()
             if user:
                 return user
    
    # If we fall through
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication credentials",
    )
