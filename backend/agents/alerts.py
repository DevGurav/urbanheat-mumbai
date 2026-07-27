"""Alert persistence + dedupe for the Monitoring agent (`agents.md` §7 — "one alert per event,
not per run"). Files, not a DB (ADR-0004; Supabase takes this over in Phase 6 without changing
`check_and_log`'s signature — only where the state and log persist).

**State** (`alerts_state.json`) — the last date checked and the last severity seen, so today's
check can tell "still the same event" from "a fresh one."
**Log** (`alerts.jsonl`) — one JSON line per *new or escalated* alert, append-only; this is
what `GET /alerts` reads.

**Dedupe rule.** A heat wave that continues at the same (or a lower) severity across
consecutive days is one event — logged once, at onset. A day where severity *increases*
(advisory → heat_wave → severe_heat_wave) is treated as new information worth its own log
entry, even mid-event. Multiple checks on the same day (a manual re-run, a retried cron)
never produce a second entry for that day, since state is compared, not run count.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

from backend.agents.monitoring import HeatwaveAlert, check_heatwave
from backend.store import Store
from data_pipeline.config import get_settings

log = logging.getLogger("urbanheat.agents.alerts")

_SEVERITY_ORDER = {"advisory": 1, "heat_wave": 2, "severe_heat_wave": 3}

STATE_FILENAME = "alerts_state.json"
LOG_FILENAME = "alerts.jsonl"


def _default_dir() -> Path:
    return get_settings().processed_dir


def _load_state(state_dir: Path) -> dict:
    path = state_dir / STATE_FILENAME
    if not path.exists():
        return {"last_checked_date": None, "last_severity": None}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(state_dir: Path, state: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / STATE_FILENAME).write_text(json.dumps(state), encoding="utf-8")


def _append_log(state_dir: Path, alert: HeatwaveAlert, today: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    entry = {"date": today, **asdict(alert)}
    with (state_dir / LOG_FILENAME).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_alerts(state_dir: Path | None = None, limit: int = 50) -> list[dict]:
    """The most recent logged alerts, newest first — what `GET /alerts` serves."""
    directory = state_dir or _default_dir()
    path = directory / LOG_FILENAME
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    return list(reversed(entries))[:limit]


def check_and_log(
    store: Store, llm: BaseChatModel | None = None, state_dir: Path | None = None
) -> HeatwaveAlert | None:
    """Run the deterministic check; log a new entry only on a fresh event or an escalation.
    Always updates state, even on a no-trigger day, so tomorrow's check has an accurate
    "yesterday" to compare against.
    """
    directory = state_dir or _default_dir()
    today = datetime.now(UTC).date().isoformat()
    state = _load_state(directory)

    alert = check_heatwave(store, llm=llm)

    if alert is None:
        _save_state(directory, {"last_checked_date": today, "last_severity": None})
        return None

    last_severity = state.get("last_severity")
    is_new_event = last_severity is None
    is_escalation = (
        last_severity is not None
        and _SEVERITY_ORDER[alert.severity] > _SEVERITY_ORDER[last_severity]
    )
    if is_new_event or is_escalation:
        _append_log(directory, alert, today)
        log.info("monitoring: logged %s alert (%s)", alert.severity, today)
    else:
        log.info(
            "monitoring: %s continues at %s severity, not re-logged (dedupe)",
            today,
            alert.severity,
        )

    _save_state(directory, {"last_checked_date": today, "last_severity": alert.severity})
    return alert
