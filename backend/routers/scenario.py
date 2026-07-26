"""POST /scenario — the digital twin, wrapping data_pipeline/ml/scenario.py (api-reference.md).

Two levers, two mechanisms (ml-methodology.md §6): greening goes through the trained model
(SHAP-validated NDVI cooling); cool-roof bypasses the model entirely and uses a cited
coefficient (Li et al. 2014), because the model's own albedo term is confounded by land cover
(ADR-0008). Every greening prediction is clamped to the citywide training envelope, and the
`clamped` field discloses it — a silently capped number that looks real is exactly the failure
mode that field exists to prevent (ADR-0006).

No cost field: `references.md` has no cited cost-per-area figure for either lever yet, and
"a cost or ΔLST figure without a source is a fabrication" (references.md) applies here as much
as it does to the cooling coefficients themselves. Add one only once a source is logged.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.errors import api_error
from backend.schemas import ScenarioCell, ScenarioRequest, ScenarioResponse
from data_pipeline.ml.dataset import TRAIN_MIN_LAND
from data_pipeline.ml.scenario import (
    cool_roof_delta,
    greening_clamped_mask,
    greening_delta,
    training_envelope,
)

router = APIRouter(tags=["model"])

CAVEATS = {
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


@router.post("/scenario", response_model=ScenarioResponse)
def scenario(request: Request, body: ScenarioRequest) -> ScenarioResponse:
    store = request.app.state.store
    features = store.features

    if body.ward_code not in set(features["ward_code"]):
        raise api_error(404, "ward_not_found", f"no ward with ward_code={body.ward_code!r}")

    all_land = features[features["land_fraction"] >= TRAIN_MIN_LAND]
    land = all_land[all_land["ward_code"] == body.ward_code].reset_index(drop=True)
    if land.empty:
        raise api_error(
            404,
            "ward_has_no_land_cells",
            f"ward {body.ward_code!r} has no cells above the training land-fraction threshold",
        )

    feature_names = store.model_meta["feature_names"]

    if body.intervention == "greening":
        envelope = training_envelope(all_land, feature_names)
        raw = greening_delta(land, store.model, feature_names, envelope)
        dlst = raw.clip(upper=0.0)  # greening cannot warm a cell all-else-equal (ml/scenario.py)
        clamped_cells = int(greening_clamped_mask(land, feature_names, envelope).sum())
    else:
        dlst = cool_roof_delta(land, coverage=body.coverage)
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
        ward_code=body.ward_code,
        intervention=body.intervention,
        coverage=body.coverage,
        n_cells=len(land),
        mean_dlst=round(float(dlst.mean()), 3),
        best_dlst=round(float(dlst.min()), 3),
        clamped=clamped_cells > 0,
        clamped_cells=clamped_cells,
        caveat=CAVEATS[body.intervention],
        model_version=store.model_version,
        cells=cells,
    )
