"""POST /reports/generate (Phase 7, `api-reference.md`).

Router-behavior tests mock `generate_ward_report` where the router looks it up
(`backend.routers.reports`, not `backend.reports.generate` — `from ... import` binds a local
name, patching the source module doesn't reach it) — they never need WeasyPrint's native
Pango/cairo libraries, only `backend/services.py`'s real ward A. The one real-rendering test
does need those libraries and skips cleanly if they're not importable (present in the
deployed Docker image and CI, not guaranteed on every dev machine —
`backend/reports/generate.py`'s module docstring has the detail).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.routers import reports as reports_router


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


def test_report_ward_only_returns_pdf(client, monkeypatch):
    monkeypatch.setattr(
        reports_router, "generate_ward_report", lambda ward, scenario: b"%PDF-fake"
    )

    resp = client.post("/reports/generate", json={"ward_code": "A"})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert 'filename="urbanheat-ward-A-report.pdf"' in resp.headers["content-disposition"]
    assert resp.content == b"%PDF-fake"


def test_report_with_intervention_calls_scenario(client, monkeypatch):
    from backend import services

    captured = {}
    real_scenario = services.scenario

    def spy_scenario(store, ward_code, intervention, coverage):
        captured["called"] = (ward_code, intervention, coverage)
        return real_scenario(store, ward_code, intervention, coverage)

    monkeypatch.setattr(services, "scenario", spy_scenario)
    monkeypatch.setattr(
        reports_router,
        "generate_ward_report",
        lambda ward, scenario: b"%PDF-fake",
    )

    resp = client.post(
        "/reports/generate",
        json={"ward_code": "A", "intervention": "cool_roof", "coverage": 0.5},
    )

    assert resp.status_code == 200
    assert captured["called"] == ("A", "cool_roof", 0.5)


def test_report_without_intervention_skips_scenario(client, monkeypatch):
    from backend import services

    scenario_mock = MagicMock()
    monkeypatch.setattr(services, "scenario", scenario_mock)
    monkeypatch.setattr(
        reports_router,
        "generate_ward_report",
        lambda ward, scenario: b"%PDF-fake",
    )

    resp = client.post("/reports/generate", json={"ward_code": "A"})

    assert resp.status_code == 200
    scenario_mock.assert_not_called()


def test_report_unknown_ward_is_404(client):
    resp = client.post("/reports/generate", json={"ward_code": "ZZ"})
    assert resp.status_code == 404


def test_report_503s_when_native_pdf_libs_unavailable(client, monkeypatch):
    def raise_oserror(ward, scenario):
        raise OSError("cannot load library 'libgobject-2.0-0'")

    monkeypatch.setattr(reports_router, "generate_ward_report", raise_oserror)

    resp = client.post("/reports/generate", json={"ward_code": "A"})

    assert resp.status_code == 503
    assert resp.json()["error_code"] == "reports_unavailable"


def test_generate_ward_report_renders_a_real_pdf(store):
    """The one test that actually calls WeasyPrint — skips if the native libs this machine
    doesn't have aren't importable, rather than failing the whole suite over an environment
    gap the deployed image and CI both close (Dockerfile, ci.yml).
    """
    try:
        from weasyprint import HTML  # noqa: F401
    except OSError as exc:
        pytest.skip(f"WeasyPrint native libraries not available: {exc}")

    from backend import services
    from backend.reports.generate import generate_ward_report

    ward = services.explain_ward(store, "A")
    scenario = services.scenario(store, "A", "greening", 1.0)

    pdf_bytes = generate_ward_report(ward, scenario)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000
