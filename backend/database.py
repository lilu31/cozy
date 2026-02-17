from sqlmodel import create_engine, Session
import os

# Use environment variables or default to localhost settings
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cozy_user:cozy_password@localhost:5432/cozy_db")

engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session
