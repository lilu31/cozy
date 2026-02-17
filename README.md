# Cozy 🏠⚡️

Cozy is a modern Home Energy Management System (HEMS) MVP designed to optimize energy usage, maximize savings, and provide a beautiful, real-time overview of your home's energy flow.

## ✨ Features

- **Real-Time Visualization**: Animated "Energy Flow" dashboard showing Solar, Grid, Battery, Home Load, and EV activity.
- **AI Optimization**: Uses linear programming (`ortools`) to schedule battery charging/discharging based on dynamic electricity prices (Day-Ahead Market).
- **Realistic Simulation**: Simulates home load profiles with morning and evening peaks.
- **Financial Tracking**: Tracks real-time savings compared to a "dumb" benchmark (no battery/smart control).
- **Asset Management**: Supports PV (Solar), Battery, and EV assets.

## 🛠 Tech Stack

- **Frontend**: [Flutter](https://flutter.dev) (Web & Mobile)
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database**: [TimescaleDB](https://www.timescale.com/) (PostgreSQL extension for time-series)
- **Optimization**: Google OR-Tools

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Flutter SDK

### 1. Backend Setup

The backend handles data simulation, optimization, and API serving.

```bash
# 1. Start Database
docker-compose up -d

# 2. Create Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary sqlmodel pandas numpy ortools

# 4. Initialize & Seed Data
python backend/init_db.py       # Create tables
python backend/clean_and_seed.py # Seed current month's data
python backfill_history.py      # Generate optimized history for the last 14 days

# 5. Run Server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

### 2. Frontend Setup

The frontend is a Flutter app.

```bash
cd app

# 1. Install Dependencies
flutter pub get

# 2. Run in Chrome (Recommended for MVP)
flutter run -d chrome
```

## 📸 Screenshots

*(Add screenshots here)*

## 🔮 Future Roadmap

- [ ] Connect to real hardware interfaces (Modbus/MQTT).
- [ ] Integrate live weather forecasts for better solar prediction.
- [ ] Multi-user tenancy support.
- [ ] Mobile-native build (iOS/Android).
