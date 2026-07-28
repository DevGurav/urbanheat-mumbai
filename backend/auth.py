"""Supabase JWT verification (Phase 6 kickoff, PROGRESS.md's Auth task).

`get_current_user` confirms a request's bearer token is a live Supabase session by asking
Supabase's own Auth API (`GET /auth/v1/user`), rather than decoding the JWT's signature
locally. That trade was made deliberately, not by default: it needs no secret beyond the
`SUPABASE_ANON_KEY` already in `.env`, at the cost of one network round-trip per authenticated
request — an acceptable trade at this project's traffic, and consistent with the session's
running preference for fewer credentials to manage (ADR-0011 dropped the Groq fallback for
exactly this reason).

Every read endpoint (map, analytics, chat, alerts) stays open and unauthenticated
(`api-reference.md`); this dependency only ever gates the write endpoints Phase 6 adds.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
from fastapi import Header

from backend.errors import api_error
from data_pipeline.config import get_settings

_AUTH_TIMEOUT_S = 10


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str | None


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUser:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise api_error(503, "auth_not_configured", "Supabase is not configured on this server")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise api_error(401, "unauthenticated", "Missing bearer token")
    token = authorization.split(" ", 1)[1]

    try:
        resp = requests.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={"Authorization": f"Bearer {token}", "apikey": settings.supabase_anon_key},
            timeout=_AUTH_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise api_error(503, "auth_upstream_unavailable", str(exc)) from exc

    if resp.status_code == 401:
        raise api_error(401, "invalid_token", "Session expired or invalid")
    resp.raise_for_status()

    body = resp.json()
    return AuthUser(id=body["id"], email=body.get("email"))
