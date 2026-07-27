"""GET /weather — Open-Meteo forecast passthrough, TTL-cached (api-reference.md).

Distinct from `data_pipeline/sources/weather.py`, which builds *historical* dry-season means
as a model feature. This endpoint is dashboard context: "what's the weather doing right now",
not a model input — so it hits Open-Meteo's forecast API for one city-representative point
rather than the pipeline's per-cell grid (the pipeline stage's own finding is that ERA5-scale
weather barely varies across the 458 km² study area — data-dictionary.md).

Fetch + cache logic lives in `backend/services.py` (ADR-0009 — the same function the Phase 4
agent toolbelt calls in-process); this router just wires the request.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend import services
from backend.schemas import WeatherResponse

router = APIRouter(tags=["data"])


@router.get("/weather", response_model=WeatherResponse)
def weather(days: int = Query(7, ge=1, le=16)) -> WeatherResponse:
    return services.get_weather(days)
