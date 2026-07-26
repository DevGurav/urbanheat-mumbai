"""GET /explain/{cell_id} — per-cell SHAP attribution, the product's answer to "why" a cell
is hot (api-reference.md). Reads straight off the store's `shap` and `features` frames — no
recomputation at request time (ADR-0004: artifacts are files, loaded once).
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from backend.errors import api_error
from backend.schemas import Driver, ExplainResponse
from data_pipeline.ml.dataset import TRAIN_MIN_LAND

router = APIRouter(tags=["data"])


@router.get("/explain/{cell_id}", response_model=ExplainResponse)
def explain_cell(
    request: Request,
    cell_id: int,
    top: int = Query(3, ge=1, le=10, description="How many drivers to return, ranked by |SHAP|"),
) -> ExplainResponse:
    store = request.app.state.store
    features = store.features

    match = features.loc[features["cell_id"] == cell_id]
    if match.empty:
        raise api_error(404, "cell_not_found", f"no cell with cell_id={cell_id}")
    cell = match.iloc[0]

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

    land = features[features["land_fraction"] >= TRAIN_MIN_LAND]
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
