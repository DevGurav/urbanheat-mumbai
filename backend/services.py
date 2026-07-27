"""The backend's actual logic — one implementation, two callers.

Every router in `backend/routers/` is a thin FastAPI wrapper around a function here: it pulls
`store` off `request.app.state.store`, calls into this module, and returns the result. The
Phase 4 agent toolbelt (`backend/agents/tools.py`) calls the same functions directly, in the
same process, with a `store` reference of its own (ADR-0009 — in-process, no HTTP loopback).
Neither caller re-implements the logic; both call it.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
import requests

from backend.cache import TTLCache
from backend.errors import api_error
from backend.schemas import (
    CellStatsResponse,
    Driver,
    ExplainResponse,
    HotspotEntry,
    HotspotsResponse,
    PredictResponse,
    ScenarioCell,
    ScenarioResponse,
    TrendsResponse,
    WardDriver,
    WardExplainResponse,
    WeatherDay,
    WeatherResponse,
)
from backend.store import Store
from data_pipeline.ml.dataset import TRAIN_MIN_LAND
from data_pipeline.ml.scenario import (
    cool_roof_delta,
    greening_clamped_mask,
    greening_delta,
    training_envelope,
)

# --- hotspots -----------------------------------------------------------------------------


def _top_driver(shap_row: pd.Series, shap_cols: list[str]) -> tuple[str, float]:
    """The feature with the largest |SHAP| for one cell, and its signed value."""
    vals = shap_row[shap_cols]
    top_col = vals.abs().idxmax()
    return top_col.removeprefix("shap_"), float(vals[top_col])


def hotspots(
    store: Store,
    n: int = 10,
    by: Literal["hvi", "lst"] = "hvi",
    unit: Literal["ward", "cell"] = "ward",
) -> HotspotsResponse:
    shap_cols = [c for c in store.shap.columns if c != "cell_id"]

    if by == "hvi":
        base = store.hvi[["cell_id", "ward_code", "hvi"]].merge(
            store.features[["cell_id", "population"]], on="cell_id", how="left"
        )
        value_col = "hvi"
    else:
        base = store.features[["cell_id", "ward_code", "lst_mean", "population"]].copy()
        value_col = "lst_mean"

    shap_by_cell = store.shap.set_index("cell_id")
    entries: list[HotspotEntry] = []

    if unit == "cell":
        top = base.sort_values(value_col, ascending=False).head(n)
        for _, row in top.iterrows():
            cell_id = int(row["cell_id"])
            driver, shap_c = None, None
            if cell_id in shap_by_cell.index:
                driver, shap_c = _top_driver(shap_by_cell.loc[cell_id], shap_cols)
            entries.append(
                HotspotEntry(
                    id=str(cell_id),
                    ward_code=str(row["ward_code"]),
                    value=round(float(row[value_col]), 3),
                    population=float(row["population"]),
                    top_driver=driver,
                    top_driver_shap_c=round(shap_c, 3) if shap_c is not None else None,
                )
            )
    else:
        agg = base.groupby("ward_code").agg(
            value=(value_col, "mean"), population=("population", "sum")
        )
        top_wards = agg.sort_values("value", ascending=False).head(n)

        # Mean |SHAP| per ward per feature — the ward's dominant driver, not a single cell's.
        shap_with_ward = store.shap.merge(
            store.features[["cell_id", "ward_code"]], on="cell_id", how="left"
        )
        ward_mean_abs = shap_with_ward.groupby("ward_code")[shap_cols].apply(
            lambda g: g.abs().mean()
        )

        for ward_code, row in top_wards.iterrows():
            driver = None
            if ward_code in ward_mean_abs.index:
                driver = ward_mean_abs.loc[ward_code].idxmax().removeprefix("shap_")
            entries.append(
                HotspotEntry(
                    id=str(ward_code),
                    ward_code=str(ward_code),
                    value=round(float(row["value"]), 3),
                    population=float(row["population"]),
                    top_driver=driver,
                    top_driver_shap_c=None,  # a ward mean, not one cell's signed SHAP
                )
            )

    return HotspotsResponse(
        by=by,
        unit=unit,
        model_version=store.model_version,
        data_version=store.data_version,
        results=entries,
    )


# --- explain --------------------------------------------------------------------------------


def _find_cell(store: Store, cell_id: int) -> pd.Series:
    match = store.features.loc[store.features["cell_id"] == cell_id]
    if match.empty:
        raise api_error(404, "cell_not_found", f"no cell with cell_id={cell_id}")
    return match.iloc[0]


def explain_cell(store: Store, cell_id: int, top: int = 3) -> ExplainResponse:
    cell = _find_cell(store, cell_id)

    shap_match = store.shap.loc[store.shap["cell_id"] == cell_id]
    if shap_match.empty:
        # SHAP was only computed over training cells (land_fraction >= TRAIN_MIN_LAND,
        # ml-methodology.md §4) — a mostly-sea cell genuinely has no attribution to give.
        raise api_error(
            404,
            "cell_not_explained",
            f"cell_id={cell_id} has no SHAP attribution — below the land-fraction "
            f"training threshold ({TRAIN_MIN_LAND}), likely mostly sea",
        )
    shap_row = shap_match.iloc[0]

    land = store.features[store.features["land_fraction"] >= TRAIN_MIN_LAND]
    city_mean = float(land["lst_mean"].mean())
    lst_mean = float(cell["lst_mean"])

    shap_cols = [c for c in store.shap.columns if c != "cell_id"]
    ranked = shap_row[shap_cols].abs().sort_values(ascending=False).head(top)
    drivers = []
    for col in ranked.index:
        feature = col.removeprefix("shap_")
        shap_c = float(shap_row[col])
        drivers.append(
            Driver(
                feature=feature,
                value=float(cell[feature]),
                shap_c=round(shap_c, 3),
                direction="warming" if shap_c > 0 else "cooling",
            )
        )

    return ExplainResponse(
        cell_id=cell_id,
        ward_code=str(cell["ward_code"]),
        lst_mean=round(lst_mean, 2),
        city_mean=round(city_mean, 2),
        deviation=round(lst_mean - city_mean, 2),
        drivers=drivers,
        model_version=store.model_version,
    )


def explain_ward(store: Store, ward_code: str, top: int = 3) -> WardExplainResponse:
    """Aggregated SHAP + summary stats for a ward — new for the Phase 4 toolbelt (`agents.md`
    §3), not a wrap of an existing endpoint. The Planning Decision agent uses this to find
    *why* a ward is hot before choosing an intervention.
    """
    ward_cells = store.features.loc[store.features["ward_code"] == ward_code]
    if ward_cells.empty:
        raise api_error(404, "ward_not_found", f"no ward with ward_code={ward_code!r}")

    shap_cols = [c for c in store.shap.columns if c != "cell_id"]
    ward_shap = store.shap.merge(ward_cells[["cell_id"]], on="cell_id", how="inner")
    if ward_shap.empty:
        raise api_error(
            404,
            "ward_not_explained",
            f"ward {ward_code!r} has no cells with SHAP attribution — all below the "
            f"land-fraction training threshold ({TRAIN_MIN_LAND})",
        )

    land = store.features[store.features["land_fraction"] >= TRAIN_MIN_LAND]
    city_mean = float(land["lst_mean"].mean())
    ward_land = ward_cells[ward_cells["land_fraction"] >= TRAIN_MIN_LAND]
    lst_mean = float(ward_land["lst_mean"].mean()) if not ward_land.empty else float("nan")

    mean_shap = ward_shap[shap_cols].mean()
    mean_features = ward_cells[[c.removeprefix("shap_") for c in shap_cols]].mean()
    ranked = mean_shap.abs().sort_values(ascending=False).head(top)

    drivers = []
    for col in ranked.index:
        feature = col.removeprefix("shap_")
        shap_c = float(mean_shap[col])
        drivers.append(
            WardDriver(
                feature=feature,
                mean_value=round(float(mean_features[feature]), 3),
                mean_shap_c=round(shap_c, 3),
                direction="warming" if shap_c > 0 else "cooling",
            )
        )

    return WardExplainResponse(
        ward_code=ward_code,
        n_cells=len(ward_cells),
        lst_mean=round(lst_mean, 2),
        city_mean=round(city_mean, 2),
        deviation=round(lst_mean - city_mean, 2),
        population=float(ward_cells["population"].sum()),
        drivers=drivers,
        model_version=store.model_version,
    )


# --- cell stats -----------------------------------------------------------------------------


def cell_stats(store: Store, cell_id: int) -> CellStatsResponse:
    """The raw model-input feature vector for a cell — new for the Phase 4 toolbelt
    (`agents.md` §3). Distinct from `explain_cell`: inputs, not SHAP attribution.
    """
    cell = _find_cell(store, cell_id)
    feature_names = store.model_meta["feature_names"]
    return CellStatsResponse(
        cell_id=cell_id,
        ward_code=str(cell["ward_code"]),
        lst_mean=round(float(cell["lst_mean"]), 2),
        land_fraction=round(float(cell["land_fraction"]), 3),
        features={name: round(float(cell[name]), 4) for name in feature_names},
        model_version=store.model_version,
    )


# --- predict --------------------------------------------------------------------------------


def predict(store: Store, cell_id: int) -> PredictResponse:
    cell = _find_cell(store, cell_id)

    if cell["land_fraction"] < TRAIN_MIN_LAND:
        raise api_error(
            404,
            "cell_not_predictable",
            f"cell_id={cell_id} is below the land-fraction training threshold "
            f"({TRAIN_MIN_LAND}) — outside the model's domain, likely mostly sea",
        )

    feature_names = store.model_meta["feature_names"]
    match = store.features.loc[store.features["cell_id"] == cell_id]
    X = store.features.loc[match.index, feature_names]
    predicted = float(store.model.predict(X)[0])
    observed = float(cell["lst_mean"])

    return PredictResponse(
        cell_id=cell_id,
        ward_code=str(cell["ward_code"]),
        predicted_lst=round(predicted, 2),
        observed_lst=round(observed, 2),
        residual=round(observed - predicted, 2),
        model_version=store.model_version,
    )


# --- scenario -------------------------------------------------------------------------------

SCENARIO_CAVEATS = {
    "greening": (
        "Correlational model, SHAP-validated NDVI cooling (Grover & Singh 2015 report ~1.39 "
        "°C per unit NDVI in Indian metros). 'Cells like this but greener are cooler' — "
        "not a causal guarantee for this specific cell."
    ),
    "cool_roof": (
        "Not model-derived: the model's own albedo term is confounded by land cover "
        "(ADR-0008), so this ΔLST comes directly from a cited coefficient (Li et al. "
        "2014: ~1.7 °C surface-UHI reduction at 50% cool-roof coverage)."
    ),
}


def scenario(
    store: Store,
    ward_code: str,
    intervention: Literal["greening", "cool_roof"],
    coverage: float = 1.0,
) -> ScenarioResponse:
    features = store.features
    if ward_code not in set(features["ward_code"]):
        raise api_error(404, "ward_not_found", f"no ward with ward_code={ward_code!r}")

    all_land = features[features["land_fraction"] >= TRAIN_MIN_LAND]
    land = all_land[all_land["ward_code"] == ward_code].reset_index(drop=True)
    if land.empty:
        raise api_error(
            404,
            "ward_has_no_land_cells",
            f"ward {ward_code!r} has no cells above the training land-fraction threshold",
        )

    feature_names = store.model_meta["feature_names"]

    if intervention == "greening":
        envelope = training_envelope(all_land, feature_names)
        raw = greening_delta(land, store.model, feature_names, envelope)
        dlst = raw.clip(upper=0.0)  # greening cannot warm a cell all-else-equal (ml/scenario.py)
        clamped_cells = int(greening_clamped_mask(land, feature_names, envelope).sum())
    else:
        dlst = cool_roof_delta(land, coverage=coverage)
        clamped_cells = 0  # a formula, not a model call — nothing to clamp

    cells = [
        ScenarioCell(
            cell_id=int(cell_id), lst_mean=round(float(lst_mean), 2), dlst=round(float(d), 3)
        )
        for cell_id, lst_mean, d in zip(
            land["cell_id"], land["lst_mean"], dlst.to_numpy(), strict=True
        )
    ]

    return ScenarioResponse(
        ward_code=ward_code,
        intervention=intervention,
        coverage=coverage,
        n_cells=len(land),
        mean_dlst=round(float(dlst.mean()), 3),
        best_dlst=round(float(dlst.min()), 3),
        clamped=clamped_cells > 0,
        clamped_cells=clamped_cells,
        caveat=SCENARIO_CAVEATS[intervention],
        model_version=store.model_version,
        cells=cells,
    )


# --- weather --------------------------------------------------------------------------------

_WEATHER_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_MUMBAI_LAT, _MUMBAI_LON = 19.0760, 72.8777
_WEATHER_DAILY_VARS = (
    "temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean,"
    "wind_speed_10m_max,precipitation_sum"
)

# Open-Meteo's forecast model updates a few times a day; 30 minutes avoids hammering it on
# every dashboard/agent call without serving stale data for long.
_weather_cache = TTLCache(ttl_s=1800)


def _fetch_weather(days: int) -> dict:
    params = {
        "latitude": _MUMBAI_LAT,
        "longitude": _MUMBAI_LON,
        "daily": _WEATHER_DAILY_VARS,
        "forecast_days": days,
        "wind_speed_unit": "ms",
        "timezone": "Asia/Kolkata",
    }
    resp = requests.get(_WEATHER_FORECAST_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_weather(days: int = 7) -> WeatherResponse:
    try:
        data = _weather_cache.get_or_set(days, lambda: _fetch_weather(days))
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


# --- trends ---------------------------------------------------------------------------------


def get_trend(ward: str | None = None) -> TrendsResponse:
    """Per-year dry-season LST slopes need `lst_trend`, deferred in Phase 1 — an honest
    "not yet available" beats faking a trend off a single multi-year composite.
    """
    return TrendsResponse(
        available=False,
        note="Per-year LST trend needs `lst_trend`, deferred in Phase 1 — not built.",
    )
