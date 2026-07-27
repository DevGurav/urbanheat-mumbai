"""POST /monitoring/check — the HTTP trigger point for the daily GitHub Actions cron
(`architecture.md` §6: `GA -->|trigger| Render`; `agents.md` §7). Not reachable from
`/agent/chat`'s supervisor — Monitoring is cron-triggered, never chat-routed.

Runs `backend.agents.alerts.check_and_log` directly against `app.state.store` and its own
`get_llm()` — deliberately independent of `app.state.supervisor`, since Monitoring's
deterministic trigger has nothing to do with whether the RAG index or the chat agents are
configured (a broken/missing LLM key degrades the *wording* only, `monitoring.py`'s own
fallback — the trigger itself never depends on the LLM).
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from backend.agents.alerts import check_and_log
from backend.schemas import AlertPayload, MonitoringCheckResponse

router = APIRouter(tags=["monitoring"])


@router.post("/monitoring/check", response_model=MonitoringCheckResponse)
def monitoring_check(request: Request) -> MonitoringCheckResponse:
    store = request.app.state.store
    alert = check_and_log(store)
    if alert is None:
        return MonitoringCheckResponse(triggered=False)

    # `today`, not whatever date the dedupe log last wrote — a continuing event's most recent
    # *log* entry can be from an earlier day than this check (backend/agents/alerts.py's
    # dedupe rule), but this response describes *today's* check, not the log's onset date.
    today = datetime.now(UTC).date().isoformat()
    return MonitoringCheckResponse(triggered=True, alert=AlertPayload(date=today, **asdict(alert)))
