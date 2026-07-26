"""GET /trends — stub only, author-confirmed at the Phase 3 kickoff.

Per-year dry-season LST slopes need `lst_trend`, which needs per-year Landsat composites that
were never built in Phase 1 (deferred, PROGRESS.md). An honest "not yet available" beats faking
a trend off a single multi-year composite.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import TrendsResponse

router = APIRouter(tags=["model"])


@router.get("/trends", response_model=TrendsResponse)
def trends(ward: str | None = None) -> TrendsResponse:
    return TrendsResponse(
        available=False,
        note="Per-year LST trend needs `lst_trend`, deferred in Phase 1 — not built.",
    )
