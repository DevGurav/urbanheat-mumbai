"""Saved scenarios (`backend/saved_scenarios.py`, `backend/routers/scenarios.py`,
PROGRESS.md's Phase 6 "Saved scenarios" task). Every scenario monkeypatches
`backend.auth.get_settings`/`backend.auth.requests` (to fake the login check) and
`backend.saved_scenarios.requests` (to fake PostgREST) so none of this depends on a live
Supabase project — same approach as `tests/test_auth.py`.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend import auth as auth_module
from backend import saved_scenarios as store_module


def _fake_settings(**overrides):
    base = dict(
        supabase_url="https://project.supabase.co",
        supabase_anon_key="anon-key",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _row(**overrides) -> dict:
    row = {
        "id": "row-1",
        "ward_code": "L",
        "intervention": "greening",
        "coverage": 1.0,
        "saved_at": "2026-07-28T12:00:00+00:00",
    }
    row.update(overrides)
    return row


# --- backend.saved_scenarios, called directly ------------------------------------------------


def test_list_saved_scenarios_returns_rows(monkeypatch):
    monkeypatch.setattr(store_module, "get_settings", _fake_settings)
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = [_row()]
    captured = {}

    def fake_get(url, headers, params, timeout):
        captured["headers"] = headers
        captured["params"] = params
        return fake_response

    monkeypatch.setattr(store_module.requests, "get", fake_get)

    rows = store_module.list_saved_scenarios("user-token")
    assert rows == [_row()]
    assert captured["headers"]["Authorization"] == "Bearer user-token"
    assert captured["params"]["order"] == "saved_at.desc"


def test_create_saved_scenario_sends_user_id_and_fields(monkeypatch):
    from backend.schemas import SavedScenarioRequest

    monkeypatch.setattr(store_module, "get_settings", _fake_settings)
    fake_response = MagicMock(status_code=201)
    fake_response.json.return_value = [_row(intervention="cool_roof", coverage=0.5)]
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return fake_response

    monkeypatch.setattr(store_module.requests, "post", fake_post)

    req = SavedScenarioRequest(ward_code="L", intervention="cool_roof", coverage=0.5)
    row = store_module.create_saved_scenario("user-token", "user-42", req)

    assert row["intervention"] == "cool_roof"
    assert captured["json"] == {
        "user_id": "user-42",
        "ward_code": "L",
        "intervention": "cool_roof",
        "coverage": 0.5,
    }


def test_delete_saved_scenario_true_when_a_row_comes_back(monkeypatch):
    monkeypatch.setattr(store_module, "get_settings", _fake_settings)
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = [_row()]
    monkeypatch.setattr(store_module.requests, "delete", lambda *a, **kw: fake_response)

    assert store_module.delete_saved_scenario("user-token", "row-1") is True


def test_delete_saved_scenario_false_when_rls_hides_the_row(monkeypatch):
    # Deleting someone else's id, or an id that doesn't exist, both come back as zero rows —
    # RLS doesn't distinguish "not found" from "not yours" (backend/saved_scenarios.py).
    monkeypatch.setattr(store_module, "get_settings", _fake_settings)
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = []
    monkeypatch.setattr(store_module.requests, "delete", lambda *a, **kw: fake_response)

    assert store_module.delete_saved_scenario("user-token", "not-mine") is False


def test_upstream_network_failure_is_503(monkeypatch):
    import requests

    monkeypatch.setattr(store_module, "get_settings", _fake_settings)

    def _raise(*a, **kw):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(store_module.requests, "get", _raise)

    with pytest.raises(Exception) as exc_info:
        store_module.list_saved_scenarios("user-token")
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["error_code"] == "scenarios_upstream_unavailable"


# --- the three endpoints, via the real app -----------------------------------------------------


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


def _authenticate(monkeypatch, user_id: str = "user-42") -> None:
    """Makes `Depends(get_current_user)` succeed for the `client` fixture's app instance
    without a real Supabase login — mocks the same `/auth/v1/user` check `test_auth.py` does.
    """
    monkeypatch.setattr(auth_module, "get_settings", _fake_settings)
    fake_user_response = MagicMock(status_code=200)
    fake_user_response.json.return_value = {"id": user_id, "email": "planner@example.com"}
    monkeypatch.setattr(auth_module.requests, "get", lambda *a, **kw: fake_user_response)
    monkeypatch.setattr(store_module, "get_settings", _fake_settings)


def test_get_scenarios_requires_auth(client):
    resp = client.get("/scenarios")
    assert resp.status_code == 401


def test_post_scenarios_creates_and_returns_the_row(client, monkeypatch):
    _authenticate(monkeypatch)
    fake_create_response = MagicMock(status_code=201)
    fake_create_response.json.return_value = [_row()]
    monkeypatch.setattr(store_module.requests, "post", lambda *a, **kw: fake_create_response)

    resp = client.post(
        "/scenarios",
        json={"ward_code": "L", "intervention": "greening", "coverage": 1.0},
        headers={"Authorization": "Bearer sometoken"},
    )

    assert resp.status_code == 201
    assert resp.json()["ward_code"] == "L"


def test_get_scenarios_lists_rows(client, monkeypatch):
    # backend.auth and backend.saved_scenarios both call `requests.get` on the *same* shared
    # `requests` module object — the login check (GET /auth/v1/user) and this listing call
    # (GET /rest/v1/saved_scenarios) can't be mocked with two separate monkeypatch.setattr
    # calls on `.get`, the second would silently clobber the first. One dispatcher, keyed on
    # URL, stands in for both.
    _authenticate(monkeypatch)
    fake_user_response = MagicMock(status_code=200)
    fake_user_response.json.return_value = {"id": "user-42", "email": "planner@example.com"}
    fake_list_response = MagicMock(status_code=200)
    fake_list_response.json.return_value = [_row(), _row(id="row-2")]

    def fake_get(url, *a, **kw):
        return fake_user_response if "auth/v1/user" in url else fake_list_response

    monkeypatch.setattr(store_module.requests, "get", fake_get)

    resp = client.get("/scenarios", headers={"Authorization": "Bearer sometoken"})

    assert resp.status_code == 200
    assert len(resp.json()["scenarios"]) == 2


def test_delete_scenarios_404s_when_nothing_was_deleted(client, monkeypatch):
    _authenticate(monkeypatch)
    fake_delete_response = MagicMock(status_code=200)
    fake_delete_response.json.return_value = []
    monkeypatch.setattr(store_module.requests, "delete", lambda *a, **kw: fake_delete_response)

    resp = client.delete("/scenarios/not-mine", headers={"Authorization": "Bearer sometoken"})

    assert resp.status_code == 404
    assert resp.json()["error_code"] == "scenario_not_found"


def test_delete_scenarios_succeeds_when_a_row_is_deleted(client, monkeypatch):
    _authenticate(monkeypatch)
    fake_delete_response = MagicMock(status_code=200)
    fake_delete_response.json.return_value = [_row()]
    monkeypatch.setattr(store_module.requests, "delete", lambda *a, **kw: fake_delete_response)

    resp = client.delete("/scenarios/row-1", headers={"Authorization": "Bearer sometoken"})

    assert resp.status_code == 204
