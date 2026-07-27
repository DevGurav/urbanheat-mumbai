"""GET /alerts — the logged Monitoring feed (`api-reference.md`, `agents.md` §7). Polled, not
pushed (ADR-0003): the dashboard reads this on a timer, nothing streams it.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.agents.alerts import read_alerts
from backend.schemas import AlertPayload, AlertsResponse

router = APIRouter(tags=["data"])


@router.get("/alerts", response_model=AlertsResponse)
def alerts(limit: int = Query(50, ge=1, le=200)) -> AlertsResponse:
    return AlertsResponse(alerts=[AlertPayload(**entry) for entry in read_alerts(limit=limit)])
