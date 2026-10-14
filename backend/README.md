# Backend — Climate Hazard Trend Analyzer API

FastAPI service providing historical multi-hazard climate risk analysis (Heatwaves, Extreme Rainfall, Drought Spells) powered by Open-Meteo reanalysis data and MongoDB caching with automatic in-memory fallback.

## Local Setup

### 1. Environment & Dependencies
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run API Server
```powershell
uvicorn app.main:app --reload --port 8000
```
- API Docs (Swagger): [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- API Health Check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

## Run Automated Tests
```powershell
python -m unittest discover -s tests
```
Runs the 19 automated test cases covering math, climatology, input validation, and API routes.

## Available Endpoints
- `GET /api/health` — System status, database mode, cache metrics.
- `GET /api/regions` — Metropolitan presets (Indian & global cities).
- `GET /api/analysis/heatwave` — 3+ consecutive days > regional 95th percentile daily max temp.
- `GET /api/analysis/rainfall` — Extreme heavy precipitation days (WMO R95p index).
- `GET /api/analysis/drought` — Meteorological drought spells (Consecutive Dry Days >= 15 days).
- `GET /api/analysis` — Generic hazard query router (`hazard=heatwave|rainfall|drought`).
