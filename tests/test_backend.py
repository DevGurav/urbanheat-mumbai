"""The backend boots, loads the store, and serves /health. Skips cleanly if the artifacts or
config aren't present (fresh clone)."""

import pytest


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    try:
        from backend.main import app

        with TestClient(app) as test_client:  # entering runs the lifespan → loads the store
            yield test_client
    except FileNotFoundError as exc:
        pytest.skip(f"artifacts not built: {exc}")
    except Exception as exc:  # noqa: BLE001 - a missing .env should skip, not error
        if ".env" in str(exc) or "config" in str(exc).lower():
            pytest.skip(str(exc))
        raise


def test_health_reports_ok_and_versions(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["n_cells"] == 11944
    assert body["model_version"].startswith("xgboost")
    assert len(body["data_version"]) == 8  # YYYYMMDD


def test_openapi_schema_is_served(client):
    assert client.get("/openapi.json").status_code == 200
