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


class PredictResponse(BaseModel):
    """The model's own LST prediction for a cell, alongside the observed value."""

    cell_id: int
    ward_code: str
    predicted_lst: float
    observed_lst: float
    residual: float = Field(description="observed - predicted")
    measurement: str = MEASUREMENT
    model_version: str


class ScenarioRequest(BaseModel):
    ward_code: str
    intervention: Literal["greening", "cool_roof"]
    coverage: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Cool-roof coverage fraction (0-1). Ignored for greening, which always raises "
            "NDVI to a fixed target rather than a coverage fraction (ml/scenario.py)."
        ),
    )


class ScenarioCell(BaseModel):
    cell_id: int
    lst_mean: float
    dlst: float = Field(description="Predicted change in surface temperature, °C")


class ScenarioResponse(BaseModel):
    ward_code: str
    intervention: Literal["greening", "cool_roof"]
    coverage: float
    measurement: str = MEASUREMENT
    n_cells: int
    mean_dlst: float
    best_dlst: float
    clamped: bool = Field(description="Whether any cell's feature vector needed clamping")
    clamped_cells: int
    caveat: str
    model_version: str
    cells: list[ScenarioCell]


class TrendsResponse(BaseModel):
    available: bool = False
    note: str


class CellStatsResponse(BaseModel):
    """A cell's raw model-input feature vector, for the agent toolbelt's `get_cell_stats`
    (`agents.md` §3) — distinct from `/explain`, which returns SHAP attribution, not inputs.
    """

    cell_id: int
    ward_code: str
    lst_mean: float
    measurement: str = MEASUREMENT
    land_fraction: float
    features: dict[str, float] = Field(description="The model's own input feature vector")
    model_version: str


class WardDriver(BaseModel):
    """One feature's aggregated contribution across a ward's cells — the ward-level analogue
    of `Driver`, which is per-cell. Values are means, not one cell's signed SHAP.
    """

    feature: str
    mean_value: float = Field(description="Mean of the feature's raw value across ward cells")
    mean_shap_c: float = Field(description="Mean signed SHAP contribution in °C across cells")
    direction: Literal["warming", "cooling"]


class WardExplainResponse(BaseModel):
    """Aggregated SHAP + summary stats for a ward — the agent toolbelt's `explain_ward`
    (`agents.md` §3), used by the Planning Decision agent to find *why* a ward is hot.
    """

    ward_code: str
    n_cells: int
    lst_mean: float
    city_mean: float = Field(description="Mean lst_mean over land cells (land_fraction >= 0.5)")
    deviation: float
    population: float
    measurement: str = MEASUREMENT
    drivers: list[WardDriver]
    model_version: str
