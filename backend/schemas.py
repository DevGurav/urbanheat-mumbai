"""Pydantic response models — the typed contracts FastAPI renders into the OpenAPI schema.

Every response that carries model output includes `model_version` and `data_version`, and any
temperature field is labelled *surface* temperature (`measurement`) so a client cannot mistake
it for air temperature (ADR-0005, api-reference conventions).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MEASUREMENT = "land_surface_temperature"


class Health(BaseModel):
    status: str = "ok"
    model_version: str
    data_version: str
    uptime_s: int
    n_cells: int = Field(description="Cells loaded in the in-memory store")


class Driver(BaseModel):
    """One feature's contribution to a cell's predicted LST (SHAP, in °C)."""

    feature: str
    value: float = Field(description="The feature's raw value for this cell")
    shap_c: float = Field(description="SHAP contribution in °C — signed, sums to the deviation")
    direction: Literal["warming", "cooling"]


class ExplainResponse(BaseModel):
    cell_id: int
    ward_code: str
    lst_mean: float
    city_mean: float = Field(description="Mean lst_mean over land cells (land_fraction >= 0.5)")
    deviation: float
    measurement: str = MEASUREMENT
    drivers: list[Driver]
    model_version: str


class HotspotEntry(BaseModel):
    """One ranked entry — a cell or a ward, depending on `unit`."""

    id: str = Field(description="cell_id (unit=cell) or ward_code (unit=ward)")
    ward_code: str
    value: float
    population: float
    top_driver: str | None = Field(
        default=None, description="Feature with the largest |SHAP|; null if unexplained"
    )
    top_driver_shap_c: float | None = Field(
        default=None, description="Signed SHAP contribution in °C; cell unit only"
    )


class HotspotsResponse(BaseModel):
    by: Literal["hvi", "lst"]
    unit: Literal["ward", "cell"]
    model_version: str
    data_version: str
    results: list[HotspotEntry]


class WeatherDay(BaseModel):
    date: str
    temp_max_c: float
    temp_min_c: float
    humidity_mean_pct: float
    wind_speed_max_ms: float
    precipitation_sum_mm: float


class WeatherResponse(BaseModel):
    source: str = "open-meteo"
    days: list[WeatherDay]
