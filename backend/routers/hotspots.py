"""GET /hotspots — ranked wards or cells by HVI or LST, each with its top SHAP driver
(api-reference.md). The ranking logic lives in `backend/services.py` (ADR-0009 — the same
function the Phase 4 agent toolbelt calls in-process); this router just wires the request.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request

from backend import services
from backend.schemas import HotspotsResponse

router = APIRouter(tags=["data"])


@router.get("/hotspots", response_model=HotspotsResponse)
def hotspots(
    request: Request,
    n: int = Query(10, ge=1, le=100),
    by: Literal["hvi", "lst"] = "hvi",
    unit: Literal["ward", "cell"] = "ward",
) -> HotspotsResponse:
    return services.hotspots(request.app.state.store, n=n, by=by, unit=unit)
