"""Supabase JWT verification (`backend/auth.py`, PROGRESS.md's Phase 6 Auth task).

`get_current_user` asks Supabase's own `/auth/v1/user` endpoint whether a bearer token is a
live session, rather than decoding it locally — see `backend/auth.py`'s module docstring for
why. Every scenario here monkeypatches `backend.auth.get_settings` and `backend.auth.requests`
so no test depends on a real Supabase project existing; the real one hasn't been provisioned
yet (`PROGRESS.md`), and these tests must still pass without it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend import auth as auth_module
from backend.errors import api_error


def _fake_settings(url: str = "https://project.supabase.co", anon_key: str = "anon-key"):
    return SimpleNamespace(supabase_url=url, supabase_anon_key=anon_key)


# --- backend.auth.get_current_user, called directly -----------------------------------------


def test_missing_authorization_header_is_401(monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    with pytest.raises(Exception) as exc_info:
        auth_module.get_current_user(authorization=None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error_code"] == "unauthenticated"


def test_non_bearer_header_is_401(monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    with pytest.raises(Exception) as exc_info:
        auth_module.get_current_user(authorization="Basic abc123")
    assert exc_info.value.status_code == 401


def test_supabase_not_configured_is_503(monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", lambda: _fake_settings(url=""))

    with pytest.raises(Exception) as exc_info:
        auth_module.get_current_user(authorization="Bearer sometoken")
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["error_code"] == "auth_not_configured"


def test_expired_or_invalid_token_is_401(monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)
    fake_response = MagicMock(status_code=401)
    monkeypatch.setattr(auth_module.requests, "get", lambda *a, **kw: fake_response)

    with pytest.raises(Exception) as exc_info:
        auth_module.get_current_user(authorization="Bearer expired")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error_code"] == "invalid_token"


def test_supabase_unreachable_is_503(monkeypatch):
    import requests

    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    def _raise(*a, **kw):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(auth_module.requests, "get", _raise)

    with pytest.raises(Exception) as exc_info:
        auth_module.get_current_user(authorization="Bearer sometoken")
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["error_code"] == "auth_upstream_unavailable"


def test_valid_token_returns_the_user(monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = {"id": "user-123", "email": "planner@example.com"}
    monkeypatch.setattr(auth_module.requests, "get", lambda *a, **kw: fake_response)

    user = auth_module.get_current_user(authorization="Bearer validtoken")
    assert user.id == "user-123"
    assert user.email == "planner@example.com"
    assert user.access_token == "validtoken"


def test_api_error_helper_shape_sanity():
    # Guards the assumption every scenario above relies on: api_error raises an HTTPException
    # whose .detail is {detail, error_code} (backend/errors.py), not a bare string.
    err = api_error(401, "unauthenticated", "Missing bearer token")
    assert err.status_code == 401
    assert err.detail == {"detail": "Missing bearer token", "error_code": "unauthenticated"}


# --- GET /auth/me, via the real app -----------------------------------------------------------


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    try:
        from backend.main import app

        with TestClient(app) as test_client:
            yield test_client
    except FileNotFoundError as exc:
        pytest.skip(f"artifacts not built: {exc}")
    except Exception as exc:  # noqa: BLE001 - a missing .env should skip, not error
        if ".env" in str(exc) or "config" in str(exc).lower():
            pytest.skip(str(exc))
        raise


def test_me_endpoint_without_a_token_is_401(client, monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)

    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "unauthenticated"


def test_me_endpoint_with_a_valid_token_returns_the_user(client, monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = {"id": "user-456", "email": "resident@example.com"}
    monkeypatch.setattr(auth_module.requests, "get", lambda *a, **kw: fake_response)

    resp = client.get("/auth/me", headers={"Authorization": "Bearer validtoken"})
    assert resp.status_code == 200
    assert resp.json() == {"id": "user-456", "email": "resident@example.com"}
