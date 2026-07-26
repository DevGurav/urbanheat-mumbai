"""GET /weather — Open-Meteo forecast passthrough, TTL-cached (api-reference.md).

Distinct from `data_pipeline/sources/weather.py`, which builds *historical* dry-season means
as a model feature. This endpoint is dashboard context: "what's the weather doing right now",
not a model input — so it hits Open-Meteo's forecast API for one city-representative point
rather than the pipeline's per-cell grid (the pipeline stage's own finding is that ERA5-scale
weather barely varies across the 458 km² study area — data-dictionary.md).
"""

from __future__ import annotations

import requests
from fastapi import APIRouter, Query

from backend.cache import TTLCache
from backend.errors import api_error
from backend.schemas import WeatherDay, WeatherResponse

router = APIRouter(tags=["data"])

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MUMBAI_LAT, MUMBAI_LON = 19.0760, 72.8777
DAILY_VARS = (
    "temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean,"
    "wind_speed_10m_max,precipitation_sum"
)

# Open-Meteo's forecast model updates a few times a day; 30 minutes avoids hammering it on
# every dashboard refresh without serving stale data for long.
_cache = TTLCache(ttl_s=1800)


def _fetch(days: int) -> dict:
    params = {
        "latitude": MUMBAI_LAT,
        "longitude": MUMBAI_LON,
        "daily": DAILY_VARS,
        "forecast_days": days,
        "wind_speed_unit": "ms",
        "timezone": "Asia/Kolkata",
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


@router.get("/weather", response_model=WeatherResponse)
def weather(days: int = Query(7, ge=1, le=16)) -> WeatherResponse:
    try:
        data = _cache.get_or_set(days, lambda: _fetch(days))
    except requests.RequestException as exc:
        raise api_error(503, "weather_upstream_unavailable", str(exc)) from exc

    daily = data["daily"]
    forecast = [
        WeatherDay(
            date=date,
            temp_max_c=daily["temperature_2m_max"][i],
            temp_min_c=daily["temperature_2m_min"][i],
            humidity_mean_pct=daily["relative_humidity_2m_mean"][i],
            wind_speed_max_ms=daily["wind_speed_10m_max"][i],
            precipitation_sum_mm=daily["precipitation_sum"][i],
        )
        for i, date in enumerate(daily["time"])
    ]
    return WeatherResponse(days=forecast)
