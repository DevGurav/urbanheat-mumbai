"""Alert dedupe + persistence (`backend/agents/alerts.py`, agents.md §7) and the two HTTP
endpoints that expose it. Uses `tmp_path` for state/log files so tests never touch the real
`data/processed/alerts*` — each scenario monkeypatches `services.get_weather` to control the
forecast temperature `check_heatwave` sees, and passes a `MagicMock` LLM (or none) so no
network call happens.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend import services
from backend.schemas import WeatherDay, WeatherResponse


def _weather(temp_max_c: float) -> WeatherResponse:
    return WeatherResponse(
        days=[
            WeatherDay(
                date="2026-07-27",
                temp_max_c=temp_max_c,
                temp_min_c=temp_max_c - 8,
                humidity_mean_pct=60.0,
                wind_speed_max_ms=3.0,
                precipitation_sum_mm=0.0,
            )
        ]
    )


@pytest.fixture
def fake_llm():
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(text="A heat wave is expected. Take precautions.")
    return llm


# --- dedupe: one alert per event, not per run (agents.md §7) -----------------------------------


def test_no_trigger_is_not_logged(store, tmp_path, monkeypatch, fake_llm):
    from backend.agents.alerts import check_and_log, read_alerts

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(32.0))
    result = check_and_log(store, llm=fake_llm, state_dir=tmp_path)

    assert result is None
    assert read_alerts(state_dir=tmp_path) == []
    fake_llm.invoke.assert_not_called()


def test_a_new_event_is_logged_once(store, tmp_path, monkeypatch, fake_llm):
    from backend.agents.alerts import check_and_log, read_alerts

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(46.0))
    result = check_and_log(store, llm=fake_llm, state_dir=tmp_path)

    assert result is not None
    assert result.severity == "heat_wave"
    logged = read_alerts(state_dir=tmp_path)
    assert len(logged) == 1
    assert logged[0]["severity"] == "heat_wave"


def test_the_same_severity_continuing_is_not_re_logged(store, tmp_path, monkeypatch, fake_llm):
    from backend.agents.alerts import check_and_log, read_alerts

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(46.0))
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)  # day 1: new event, logged
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)  # day 2: same severity, continuing

    assert len(read_alerts(state_dir=tmp_path)) == 1


def test_escalation_gets_its_own_log_entry(store, tmp_path, monkeypatch, fake_llm):
    from backend.agents.alerts import check_and_log, read_alerts

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(38.0))  # advisory
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(47.5))  # severe
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)

    logged = read_alerts(state_dir=tmp_path)
    assert [e["severity"] for e in logged] == ["severe_heat_wave", "advisory"]  # newest first


def test_de_escalation_within_an_event_is_not_re_logged(store, tmp_path, monkeypatch, fake_llm):
    from backend.agents.alerts import check_and_log, read_alerts

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(47.5))  # severe
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(38.0))  # advisory
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)

    logged = read_alerts(state_dir=tmp_path)
    assert len(logged) == 1
    assert logged[0]["severity"] == "severe_heat_wave"


def test_a_fresh_event_after_a_gap_is_logged_again(store, tmp_path, monkeypatch, fake_llm):
    from backend.agents.alerts import check_and_log, read_alerts

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(46.0))
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)  # event 1: logged

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(30.0))
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)  # no trigger: resets state

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(46.0))
    check_and_log(store, llm=fake_llm, state_dir=tmp_path)  # event 2: a fresh event, logged

    logged = read_alerts(state_dir=tmp_path)
    assert len(logged) == 2


def test_read_alerts_respects_limit(store, tmp_path, monkeypatch, fake_llm):
    from backend.agents.alerts import check_and_log, read_alerts

    for temp in (46.0, 30.0, 47.5, 30.0, 38.0):
        monkeypatch.setattr(services, "get_weather", lambda days, t=temp: _weather(t))
        check_and_log(store, llm=fake_llm, state_dir=tmp_path)

    assert len(read_alerts(state_dir=tmp_path)) == 3  # 3 distinct events logged
    assert len(read_alerts(state_dir=tmp_path, limit=2)) == 2


# --- the two endpoints, via the real app -------------------------------------------------------


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


def test_monitoring_check_endpoint_reports_no_trigger_honestly(client, monkeypatch):
    monkeypatch.setattr(services, "get_weather", lambda days: _weather(30.0))
    resp = client.post("/monitoring/check")

    assert resp.status_code == 200
    assert resp.json() == {"triggered": False, "alert": None}


def test_monitoring_check_endpoint_reports_a_real_trigger(client, monkeypatch, tmp_path):
    from backend.agents import alerts as alerts_module

    monkeypatch.setattr(services, "get_weather", lambda days: _weather(46.0))
    monkeypatch.setattr(alerts_module, "_default_dir", lambda: tmp_path)

    resp = client.post("/monitoring/check")

    assert resp.status_code == 200
    body = resp.json()
    assert body["triggered"] is True
    assert body["alert"]["severity"] == "heat_wave"
    assert "not an official IMD warning" in body["alert"]["caveat"]


def test_alerts_endpoint_serves_what_was_logged(client, monkeypatch, tmp_path):
    from backend.agents import alerts as alerts_module

    monkeypatch.setattr(alerts_module, "_default_dir", lambda: tmp_path)
    monkeypatch.setattr(services, "get_weather", lambda days: _weather(46.0))
    client.post("/monitoring/check")

    resp = client.get("/alerts")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["alerts"]) == 1
    assert body["alerts"][0]["severity"] == "heat_wave"
