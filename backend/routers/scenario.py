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

Logic lives in `backend/services.py` (ADR-0009 — the same function the Phase 4 agent toolbelt
calls in-process); this router just wires the request.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend import services
from backend.schemas import ScenarioRequest, ScenarioResponse

router = APIRouter(tags=["model"])


@router.post("/scenario", response_model=ScenarioResponse)
def scenario(request: Request, body: ScenarioRequest) -> ScenarioResponse:
    return services.scenario(
        request.app.state.store,
        ward_code=body.ward_code,
        intervention=body.intervention,
        coverage=body.coverage,
    )
