from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routers import dashboard, assets, debug

app = FastAPI(title="Cozy Energy API")

# CORS
origins = ["*"] # Allow all for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(dashboard.router)
app.include_router(assets.router)
app.include_router(debug.router)

@app.get("/")
def health_check():
    return {"status": "running", "msg": "Cozy Backend Online"}
