from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://cozy_user:cozy_password@localhost:5432/cozy_db"
    
    # Feature Flags
    USE_MOCKS: bool = True
    
    # App
    PROJECT_NAME: str = "Cozy MVP"
    VERSION: str = "0.1.0"

settings = Settings()
