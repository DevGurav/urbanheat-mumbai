"""GET /explain/{cell_id} — per-cell SHAP attribution, the product's answer to "why" a cell
is hot (api-reference.md). Logic lives in `backend/services.py` (ADR-0009 — the same function
the Phase 4 agent toolbelt calls in-process); this router just wires the request.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from backend import services
from backend.schemas import ExplainResponse

router = APIRouter(tags=["data"])


@router.get("/explain/{cell_id}", response_model=ExplainResponse)
def explain_cell(
    request: Request,
    cell_id: int,
    top: int = Query(3, ge=1, le=10, description="How many drivers to return, ranked by |SHAP|"),
) -> ExplainResponse:
    return services.explain_cell(request.app.state.store, cell_id, top=top)
