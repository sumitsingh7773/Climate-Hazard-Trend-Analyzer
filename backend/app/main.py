from datetime import date, timedelta
import hashlib
import logging
from typing import Literal
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .db import (
    get_weather_records,
    save_weather_records,
    get_cached_analysis,
    save_analysis,
    get_db_status,
    get_cache_stats,
)
from .weather import fetch_weather
from .analysis import analyze_heatwaves, analyze_heavy_rainfall, analyze_drought

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("climate_analyzer")

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.api_rate_limit])
app = FastAPI(
    title="Climate Hazard Trend Analyzer API",
    description="Multi-hazard historical climate trend analysis (Heatwaves, Extreme Rainfall, Drought) using Open-Meteo archive data.",
    version="1.2.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration supporting exact Vercel frontend, localhost/127.0.0.1 on any port, and configured origin
cors_origins = [
    "https://climate-hazard-trend-analyzer-silk.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]
if settings.frontend_origin:
    for origin in settings.frontend_origin.split(","):
        clean_origin = origin.strip().rstrip("/")
        if clean_origin and clean_origin not in cors_origins:
            cors_origins.append(clean_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REGIONS_PRESET = [
    {"name": "Patna, India", "latitude": 25.5941, "longitude": 85.1376, "country": "India"},
    {"name": "Delhi, India", "latitude": 28.6139, "longitude": 77.2090, "country": "India"},
    {"name": "Mumbai, India", "latitude": 19.0760, "longitude": 72.8777, "country": "India"},
    {"name": "Kolkata, India", "latitude": 22.5726, "longitude": 88.3639, "country": "India"},
    {"name": "Ranchi, India", "latitude": 23.3441, "longitude": 85.3096, "country": "India"},
    {"name": "Bengaluru, India", "latitude": 12.9716, "longitude": 77.5946, "country": "India"},
    {"name": "Chennai, India", "latitude": 13.0827, "longitude": 80.2707, "country": "India"},
    {"name": "Ahmedabad, India", "latitude": 23.0225, "longitude": 72.5714, "country": "India"},
    {"name": "London, UK", "latitude": 51.5074, "longitude": -0.1278, "country": "United Kingdom"},
    {"name": "Phoenix, USA", "latitude": 33.4484, "longitude": -112.0740, "country": "USA"},
    {"name": "Tokyo, Japan", "latitude": 35.6762, "longitude": 139.6503, "country": "Japan"},
    {"name": "Dubai, UAE", "latitude": 25.2048, "longitude": 55.2708, "country": "UAE"},
]

@app.get("/")
def root():
    return {
        "message": "Climate Hazard Trend Analyzer API is operational",
        "docs": "/docs",
        "endpoints": [
            "/api/health",
            "/api/regions",
            "/api/analysis/heatwave",
            "/api/analysis/rainfall",
            "/api/analysis/drought",
            "/api/analysis",
        ],
    }

@app.get("/api/health")
def health_check():
    db_status = get_db_status()
    stats = get_cache_stats()
    return {
        "status": "healthy",
        "database": db_status,
        "cache_stats": stats,
    }

@app.get("/api/regions")
def get_regions():
    return {"regions": REGIONS_PRESET}

async def _get_or_fetch_records(latitude: float, longitude: float, start_date: date, end_date: date):
    location_key = f"{latitude:.3f},{longitude:.3f}"
    existing = get_weather_records(location_key, start_date.isoformat(), end_date.isoformat())
    existing_by_date = {r["date"]: r for r in existing}
    expected_days = (end_date - start_date).days + 1

    # Check if existing cache covers all days and has both temperature and rainfall
    needs_fetch = False
    if len(existing_by_date) < expected_days:
        needs_fetch = True
    else:
        # Check if records have both variables
        sample = next(iter(existing_by_date.values()), {})
        if "tmax_c" not in sample or "prcp_mm" not in sample:
            needs_fetch = True

    cache_source = "weather-cache-hit"
    if needs_fetch:
        fetched = await fetch_weather(latitude, longitude, start_date, end_date)
        save_weather_records(location_key, fetched)
        for r in fetched:
            existing_by_date[r["date"]] = r
        cache_source = "weather-fetched"

    records = sorted(existing_by_date.values(), key=lambda r: r["date"])
    return records, location_key, cache_source

def _validate_dates(start_date: date, end_date: date):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be on or before end_date")
    if (end_date - start_date).days > 366 * 70:
        raise HTTPException(status_code=400, detail="Maximum supported range is 70 years")
    min_lag_date = date.today() - timedelta(days=3)
    if end_date > min_lag_date:
        raise HTTPException(
            status_code=400,
            detail=f"Choose an end date on or before {min_lag_date.isoformat()} (historical archive has a 3-day publication lag)"
        )

@app.get("/api/analysis/heatwave")
@limiter.limit(settings.api_rate_limit)
async def heatwave_analysis(
    request: Request,
    latitude: float = Query(25.5941, ge=-90.0, le=90.0),
    longitude: float = Query(85.1376, ge=-180.0, le=180.0),
    start_date: date = Query(date(1990, 1, 1)),
    end_date: date = Query(date(2020, 12, 31)),
):
    _validate_dates(start_date, end_date)
    location_key = f"{latitude:.3f},{longitude:.3f}"
    analysis_key = hashlib.sha256(
        f"{location_key}|{start_date}|{end_date}|heatwave-v2".encode()
    ).hexdigest()

    cached = get_cached_analysis(analysis_key)
    if cached:
        cached["cache"] = "analysis-hit"
        return cached

    records, _, cache_source = await _get_or_fetch_records(latitude, longitude, start_date, end_date)
    result = analyze_heatwaves(records, start_date, end_date)
    result.update({
        "region": {"latitude": latitude, "longitude": longitude},
        "source": "Open-Meteo Historical Weather API",
        "cache": cache_source,
    })
    save_analysis(analysis_key, result)
    return result

@app.get("/api/analysis/rainfall")
@limiter.limit(settings.api_rate_limit)
async def rainfall_analysis(
    request: Request,
    latitude: float = Query(25.5941, ge=-90.0, le=90.0),
    longitude: float = Query(85.1376, ge=-180.0, le=180.0),
    start_date: date = Query(date(1990, 1, 1)),
    end_date: date = Query(date(2020, 12, 31)),
):
    _validate_dates(start_date, end_date)
    location_key = f"{latitude:.3f},{longitude:.3f}"
    analysis_key = hashlib.sha256(
        f"{location_key}|{start_date}|{end_date}|rainfall-v2".encode()
    ).hexdigest()

    cached = get_cached_analysis(analysis_key)
    if cached:
        cached["cache"] = "analysis-hit"
        return cached

    records, _, cache_source = await _get_or_fetch_records(latitude, longitude, start_date, end_date)
    result = analyze_heavy_rainfall(records, start_date, end_date)
    result.update({
        "region": {"latitude": latitude, "longitude": longitude},
        "source": "Open-Meteo Historical Weather API",
        "cache": cache_source,
    })
    save_analysis(analysis_key, result)
    return result

@app.get("/api/analysis/drought")
@limiter.limit(settings.api_rate_limit)
async def drought_analysis(
    request: Request,
    latitude: float = Query(25.5941, ge=-90.0, le=90.0),
    longitude: float = Query(85.1376, ge=-180.0, le=180.0),
    start_date: date = Query(date(1990, 1, 1)),
    end_date: date = Query(date(2020, 12, 31)),
):
    _validate_dates(start_date, end_date)
    location_key = f"{latitude:.3f},{longitude:.3f}"
    analysis_key = hashlib.sha256(
        f"{location_key}|{start_date}|{end_date}|drought-v2".encode()
    ).hexdigest()

    cached = get_cached_analysis(analysis_key)
    if cached:
        cached["cache"] = "analysis-hit"
        return cached

    records, _, cache_source = await _get_or_fetch_records(latitude, longitude, start_date, end_date)
    result = analyze_drought(records, start_date, end_date)
    result.update({
        "region": {"latitude": latitude, "longitude": longitude},
        "source": "Open-Meteo Historical Weather API",
        "cache": cache_source,
    })
    save_analysis(analysis_key, result)
    return result

@app.get("/api/analysis")
@limiter.limit(settings.api_rate_limit)
async def generic_analysis(
    request: Request,
    hazard: Literal["heatwave", "rainfall", "drought"] = Query("heatwave"),
    latitude: float = Query(25.5941, ge=-90.0, le=90.0),
    longitude: float = Query(85.1376, ge=-180.0, le=180.0),
    start_date: date = Query(date(1990, 1, 1)),
    end_date: date = Query(date(2020, 12, 31)),
):
    if hazard == "heatwave":
        return await heatwave_analysis(request, latitude, longitude, start_date, end_date)
    elif hazard == "rainfall":
        return await rainfall_analysis(request, latitude, longitude, start_date, end_date)
    elif hazard == "drought":
        return await drought_analysis(request, latitude, longitude, start_date, end_date)
    raise HTTPException(status_code=400, detail=f"Unsupported hazard: {hazard}")
