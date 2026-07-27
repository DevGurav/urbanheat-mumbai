"""GET /trends — stub only, author-confirmed at the Phase 3 kickoff.

Per-year dry-season LST slopes need `lst_trend`, which needs per-year Landsat composites that
were never built in Phase 1 (deferred, PROGRESS.md). An honest "not yet available" beats faking
a trend off a single multi-year composite. Logic lives in `backend/services.py` (ADR-0009 — the
same function the Phase 4 agent toolbelt calls in-process); this router just wires the request.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend import services
from backend.schemas import TrendsResponse

router = APIRouter(tags=["model"])


@router.get("/trends", response_model=TrendsResponse)
def trends(ward: str | None = None) -> TrendsResponse:
    return services.get_trend(ward)
