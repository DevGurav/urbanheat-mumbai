"""The LangChain toolbelt the four Phase 4 agents share (`agents.md` §3).

Every tool here is a thin wrapper over `backend/services.py`, called **in-process** — not the
REST API over HTTP (ADR-0009). `build_toolbelt(store)` binds each tool to one `Store` instance
(the same one FastAPI loads once at startup, `app.state.store`) so the LLM never supplies or
chooses it; only the typed, Pydantic-validated arguments below come from the LLM.

`search_knowledge` (`agents.md` §3) is not here yet — it needs the Chroma index the "RAG
knowledge base" task group builds next. Wiring a tool to a retriever that doesn't exist would
be exactly the kind of not-yet-real capability `agents.md` §1 warns against.

Every tool returns a plain dict carrying `model_version` (and `measurement` where the number is
a temperature) so the calling agent can cite, not assert — `agents.md` §3's provenance rule. A
domain error (unknown cell, a ward with no land cells, ...) comes back as
`{"error": ..., "error_code": ...}` rather than raising: a tool that raises looks like a crash
to the agent loop, while a tool that returns a labelled error lets the agent say "I couldn't
compute that" (`agents.md` §1) instead of guessing.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import HTTPException
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend import services
from backend.store import Store


def _as_tool_error(exc: HTTPException) -> dict:
    detail = exc.detail if isinstance(exc.detail, dict) else {"detail": exc.detail}
    return {"error": detail.get("detail", str(exc.detail)), "error_code": detail.get("error_code")}


def _safe_call(fn, *args: Any, **kwargs: Any) -> dict:
    try:
        result = fn(*args, **kwargs)
    except HTTPException as exc:
        return _as_tool_error(exc)
    return result.model_dump()


# --- get_hotspots -------------------------------------------------------------------------


class GetHotspotsArgs(BaseModel):
    n: int = Field(default=10, ge=1, le=100, description="How many ranked entries to return")
    by: Literal["hvi", "lst"] = Field(
        default="hvi", description="Rank by Heat Vulnerability Index or surface temperature"
    )
    unit: Literal["ward", "cell"] = Field(default="ward", description="Rank wards or cells")


def _make_get_hotspots(store: Store) -> StructuredTool:
    def get_hotspots(n: int = 10, by: str = "hvi", unit: str = "ward") -> dict:
        return _safe_call(services.hotspots, store, n=n, by=by, unit=unit)

    return StructuredTool.from_function(
        func=get_hotspots,
        name="get_hotspots",
        description=(
            "Ranked wards or cells by Heat Vulnerability Index or surface temperature, each "
            "with its top SHAP driver. The starting point for any 'where is it worst' or "
            "planning question."
        ),
        args_schema=GetHotspotsArgs,
    )


# --- get_cell_stats -------------------------------------------------------------------------


class GetCellStatsArgs(BaseModel):
    cell_id: int = Field(description="The 200 m grid cell's stable cell_id")


def _make_get_cell_stats(store: Store) -> StructuredTool:
    def get_cell_stats(cell_id: int) -> dict:
        return _safe_call(services.cell_stats, store, cell_id)

    return StructuredTool.from_function(
        func=get_cell_stats,
        name="get_cell_stats",
        description=(
            "One cell's raw model-input feature vector, surface temperature and ward — the "
            "model's *inputs*, not its explanation. Use explain_cell for why a cell is hot."
        ),
        args_schema=GetCellStatsArgs,
    )


# --- explain_cell ---------------------------------------------------------------------------


class ExplainCellArgs(BaseModel):
    cell_id: int = Field(description="The 200 m grid cell's stable cell_id")
    top: int = Field(default=3, ge=1, le=10, description="How many drivers to return")


def _make_explain_cell(store: Store) -> StructuredTool:
    def explain_cell(cell_id: int, top: int = 3) -> dict:
        return _safe_call(services.explain_cell, store, cell_id, top=top)

    return StructuredTool.from_function(
        func=explain_cell,
        name="explain_cell",
        description=(
            "SHAP attribution for one cell: which features push its surface temperature up "
            "or down, and by how many degrees. This is the product's answer to 'why is it "
            "hot here' for a specific location."
        ),
        args_schema=ExplainCellArgs,
    )


# --- explain_ward ---------------------------------------------------------------------------


class ExplainWardArgs(BaseModel):
    ward_code: str = Field(description="BMC administrative ward code, e.g. 'L' or 'H/E'")
    top: int = Field(default=3, ge=1, le=10, description="How many drivers to return")


def _make_explain_ward(store: Store) -> StructuredTool:
    def explain_ward(ward_code: str, top: int = 3) -> dict:
        return _safe_call(services.explain_ward, store, ward_code, top=top)

    return StructuredTool.from_function(
        func=explain_ward,
        name="explain_ward",
        description=(
            "Aggregated SHAP attribution + summary stats for a whole ward: mean surface "
            "temperature, population, and the drivers responsible on average. Use this before "
            "recommending an intervention — it tells you *why* a ward is hot, not just that "
            "it is."
        ),
        args_schema=ExplainWardArgs,
    )


# --- simulate_scenario ----------------------------------------------------------------------


class SimulateScenarioArgs(BaseModel):
    ward_code: str = Field(description="BMC administrative ward code, e.g. 'L' or 'H/E'")
    intervention: Literal["greening", "cool_roof"] = Field(
        description="Which lever to simulate — no other interventions are modelled yet"
    )
    coverage: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Cool-roof coverage fraction (0-1). Ignored for greening, which always raises "
            "NDVI to a fixed target rather than a coverage fraction."
        ),
    )


def _make_simulate_scenario(store: Store) -> StructuredTool:
    def simulate_scenario(ward_code: str, intervention: str, coverage: float = 1.0) -> dict:
        return _safe_call(
            services.scenario, store, ward_code, intervention=intervention, coverage=coverage
        )

    return StructuredTool.from_function(
        func=simulate_scenario,
        name="simulate_scenario",
        description=(
            "The digital twin: perturb a ward's cells with an intervention (greening or "
            "cool_roof) and re-predict surface temperature. Returns per-cell delta-LST, "
            "summary stats, and whether any cell needed clamping to the training envelope. "
            "Correlational, not causal — phrase results as 'cells like this but greener run "
            "cooler', never as a guarantee for one cell. Only ward-level scenarios are "
            "supported; per-cell targeting is not built."
        ),
        args_schema=SimulateScenarioArgs,
    )


# --- get_weather ----------------------------------------------------------------------------


class GetWeatherArgs(BaseModel):
    days: int = Field(default=7, ge=1, le=16, description="Forecast horizon in days")


def _make_get_weather(store: Store) -> StructuredTool:
    def get_weather(days: int = 7) -> dict:
        return _safe_call(services.get_weather, days=days)

    return StructuredTool.from_function(
        func=get_weather,
        name="get_weather",
        description=(
            "Open-Meteo forecast (max/min air temperature, humidity, wind, rain) for a "
            "city-representative point in Mumbai. Air temperature, not the model's surface "
            "temperature — do not conflate the two."
        ),
        args_schema=GetWeatherArgs,
    )


# --- get_trend ------------------------------------------------------------------------------


class GetTrendArgs(BaseModel):
    ward: str | None = Field(default=None, description="BMC ward code, or None for citywide")


def _make_get_trend(store: Store) -> StructuredTool:
    def get_trend(ward: str | None = None) -> dict:
        return _safe_call(services.get_trend, ward=ward)

    return StructuredTool.from_function(
        func=get_trend,
        name="get_trend",
        description=(
            "Per-year surface-temperature trend (°C/yr). Currently always reports "
            "unavailable — the per-year Landsat reduction it needs was deferred in Phase 1. "
            "Report this honestly rather than inferring a trend from anything else."
        ),
        args_schema=GetTrendArgs,
    )


_BUILDERS = (
    _make_get_hotspots,
    _make_get_cell_stats,
    _make_explain_cell,
    _make_explain_ward,
    _make_simulate_scenario,
    _make_get_weather,
    _make_get_trend,
)


def build_toolbelt(store: Store) -> list[StructuredTool]:
    """The shared toolbelt, bound to one `Store`. Call once per app/agent-graph lifetime —
    each tool closes over `store`, not a per-request lookup, since the store is loaded once at
    startup and never mutated (ADR-0004).
    """
    return [make(store) for make in _BUILDERS]
