"""One Earth Engine session, shared by every stage that needs it.

`ee.Initialize` is process-global but not free — it fetches the algorithm signatures from
Google's servers on first call. Routing every stage through `init()` means that happens
once per run instead of once per import site, and it puts the "is the project registered?"
failure in a single place with a message that says what to do about it.
"""

from __future__ import annotations

import ee

from data_pipeline.config import get_settings

_initialised = False


def init() -> str:
    """Initialise Earth Engine against the configured project. Idempotent.

    Returns the project id, so callers can log which project spent the quota.
    """
    global _initialised
    settings = get_settings()

    if _initialised:
        return settings.gee_project_id

    try:
        ee.Initialize(project=settings.gee_project_id)
    except Exception as exc:  # noqa: BLE001 - re-raised below with guidance
        # The three failures seen in practice are a missing credential file, an
        # unregistered Cloud project, and a project whose Earth Engine API was never
        # enabled. They surface as different exception types from different layers, so
        # catch broadly and point at the runbook rather than guessing which one it was.
        raise RuntimeError(
            f"Earth Engine init failed for project '{settings.gee_project_id}': {exc}\n"
            "See docs/runbook.md §6 — the usual causes are missing credentials "
            "(run `uv run earthengine authenticate --auth_mode=notebook`) or a project "
            "that was never registered at https://code.earthengine.google.com/register"
        ) from exc

    _initialised = True
    return settings.gee_project_id
