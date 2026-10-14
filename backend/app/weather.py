from datetime import date
import httpx
from fastapi import HTTPException

WEATHER_API_URL = "https://archive-api.open-meteo.com/v1/archive"

async def fetch_weather(latitude: float, longitude: float,
                        start_date: date, end_date: date) -> list[dict]:
    """
    Fetches real historical weather data from Open-Meteo Historical Weather Archive API.
    Retrieves daily maximum temperature (temperature_2m_max) and precipitation sum (precipitation_sum).
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "temperature_2m_max,precipitation_sum",
        "timezone": "UTC",
    }
    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.get(WEATHER_API_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504,
            detail="Historical weather provider request timed out. Please try a shorter date range."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Historical weather provider request failed: {str(exc)}"
        ) from exc

    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    tmax_values = daily.get("temperature_2m_max") or []
    prcp_values = daily.get("precipitation_sum") or []

    if not dates:
        raise HTTPException(
            status_code=502,
            detail="Weather provider returned no observations for the selected location and period."
        )

    records = []
    for i, day in enumerate(dates):
        tmax = tmax_values[i] if i < len(tmax_values) else None
        prcp = prcp_values[i] if i < len(prcp_values) else None
        records.append({
            "date": day,
            "tmax_c": float(tmax) if tmax is not None else None,
            "prcp_mm": float(prcp) if prcp is not None else None,
        })
    return records
