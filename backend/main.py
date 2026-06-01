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

from fastapi.staticfiles import StaticFiles
import os

# Include Routers
app.include_router(dashboard.router)
app.include_router(assets.router)
app.include_router(debug.router)

# Mount the compiled Flutter Web directory to serve static resources and index.html at root
flutter_web_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app/build/web"))
if os.path.exists(flutter_web_path):
    app.mount("/", StaticFiles(directory=flutter_web_path, html=True), name="flutter_web")
else:
    static_fallback_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
    app.mount("/", StaticFiles(directory=static_fallback_path, html=True), name="static_fallback")

