"""GET /predict — the model's own LST prediction for a cell, vs. what Landsat observed
(api-reference.md). A transparency endpoint: how far is the fitted surface from the data?
Logic lives in `backend/services.py` (ADR-0009 — the same function the Phase 4 agent toolbelt
calls in-process); this router just wires the request.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend import services
from backend.schemas import PredictResponse

router = APIRouter(tags=["model"])


@router.get("/predict", response_model=PredictResponse)
def predict(request: Request, cell_id: int) -> PredictResponse:
    return services.predict(request.app.state.store, cell_id)
