"""CRUD over Supabase's `saved_scenarios` table (Phase 6, `supabase/schema.sql`), via
PostgREST rather than the `supabase-py` SDK — one HTTP client (`requests`) for every external
call this backend makes, the same choice `backend/auth.py` and `backend/services.py`'s
`get_weather` already made.

Every call forwards the caller's own Supabase access token, not the service-role key. That
means Postgres's row-level security — not this module — is what actually stops one user from
reading, saving as, or deleting another user's scenarios: `auth.uid() = user_id` in
`supabase/schema.sql` is the real access-control boundary, this code is just the HTTP plumbing
in front of it (the same "ask Supabase" trade `backend/auth.py`'s module docstring explains).
"""

from __future__ import annotations

import requests

from backend.errors import api_error
from backend.schemas import SavedScenarioRequest
from data_pipeline.config import get_settings

_REST_TIMEOUT_S = 10


def _headers(access_token: str) -> dict[str, str]:
    settings = get_settings()
    return {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {access_token}",
    }


def list_saved_scenarios(access_token: str) -> list[dict]:
    settings = get_settings()
    try:
        resp = requests.get(
            f"{settings.supabase_url}/rest/v1/saved_scenarios",
            headers=_headers(access_token),
            params={"select": "*", "order": "saved_at.desc"},
            timeout=_REST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise api_error(503, "scenarios_upstream_unavailable", str(exc)) from exc
    resp.raise_for_status()
    return resp.json()


def create_saved_scenario(access_token: str, user_id: str, req: SavedScenarioRequest) -> dict:
    settings = get_settings()
    try:
        resp = requests.post(
            f"{settings.supabase_url}/rest/v1/saved_scenarios",
            headers={**_headers(access_token), "Prefer": "return=representation"},
            json={
                "user_id": user_id,
                "ward_code": req.ward_code,
                "intervention": req.intervention,
                "coverage": req.coverage,
            },
            timeout=_REST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise api_error(503, "scenarios_upstream_unavailable", str(exc)) from exc
    resp.raise_for_status()
    return resp.json()[0]


def delete_saved_scenario(access_token: str, scenario_id: str) -> bool:
    """True if a row was actually deleted. RLS silently returns zero rows rather than 403 for
    an id that exists but belongs to someone else, so "not found" and "not yours" look
    identical here — deliberately: telling a caller *which* is true would leak that the id
    exists.
    """
    settings = get_settings()
    try:
        resp = requests.delete(
            f"{settings.supabase_url}/rest/v1/saved_scenarios",
            headers={**_headers(access_token), "Prefer": "return=representation"},
            params={"id": f"eq.{scenario_id}"},
            timeout=_REST_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise api_error(503, "scenarios_upstream_unavailable", str(exc)) from exc
    resp.raise_for_status()
    return len(resp.json()) > 0
