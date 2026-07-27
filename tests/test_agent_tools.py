"""The Phase 4 agent toolbelt (`backend/agents/tools.py`) calls `backend/services.py` directly
— the same functions the HTTP routes call (ADR-0009). These tests exercise the tools exactly as
an agent would: `.invoke({...})`, real fixtures, no HTTP layer. Skips cleanly if the gitignored
artifacts haven't been built (fresh clone), same pattern as `test_backend.py`.
"""

import pytest

from backend.agents.tools import build_toolbelt

# A confirmed land cell with SHAP attribution, ward "A" (data/processed/features.parquet,
# reused from test_backend.py so both suites agree on what "a known land cell" means).
KNOWN_LAND_CELL = 10453001345
KNOWN_LAND_WARD = "A"
# Present in features.parquet, absent from shap_values.parquet — a real but non-land cell.
KNOWN_NON_LAND_CELL = 10452001345


@pytest.fixture
def toolbelt():
    from backend.store import load_store

    try:
        store = load_store()
    except FileNotFoundError as exc:
        pytest.skip(f"artifacts not built: {exc}")
    except Exception as exc:  # noqa: BLE001 - a missing .env should skip, not error
        if ".env" in str(exc) or "config" in str(exc).lower():
            pytest.skip(str(exc))
        raise
    return {tool.name: tool for tool in build_toolbelt(store)}


def test_toolbelt_has_seven_tools(toolbelt):
    # search_knowledge is deferred until the RAG knowledge base task builds the Chroma index.
    assert set(toolbelt) == {
        "get_hotspots",
        "get_cell_stats",
        "explain_cell",
        "explain_ward",
        "simulate_scenario",
        "get_weather",
        "get_trend",
    }


def test_get_hotspots_ranks_descending(toolbelt):
    result = toolbelt["get_hotspots"].invoke({"n": 5, "by": "hvi", "unit": "ward"})
    values = [r["value"] for r in result["results"]]
    assert values == sorted(values, reverse=True)
    assert result["model_version"]


def test_get_cell_stats_known_cell(toolbelt):
    result = toolbelt["get_cell_stats"].invoke({"cell_id": KNOWN_LAND_CELL})
    assert result["ward_code"] == KNOWN_LAND_WARD
    assert result["measurement"] == "land_surface_temperature"
    assert isinstance(result["features"], dict) and result["features"]


def test_get_cell_stats_unknown_cell_is_a_labelled_error_not_a_crash(toolbelt):
    result = toolbelt["get_cell_stats"].invoke({"cell_id": 999999999999})
    assert result["error_code"] == "cell_not_found"


def test_explain_cell_known_land_cell(toolbelt):
    result = toolbelt["explain_cell"].invoke({"cell_id": KNOWN_LAND_CELL, "top": 3})
    assert len(result["drivers"]) == 3
    assert result["deviation"] == round(result["lst_mean"] - result["city_mean"], 2)


def test_explain_cell_non_land_cell_is_a_labelled_error(toolbelt):
    result = toolbelt["explain_cell"].invoke({"cell_id": KNOWN_NON_LAND_CELL})
    assert result["error_code"] == "cell_not_explained"


def test_explain_ward_known_ward(toolbelt):
    result = toolbelt["explain_ward"].invoke({"ward_code": KNOWN_LAND_WARD, "top": 3})
    assert result["ward_code"] == KNOWN_LAND_WARD
    assert result["n_cells"] > 0
    assert len(result["drivers"]) == 3
    # deviation is rounded from the raw (unrounded) means, so it can differ from
    # round(lst_mean - city_mean, 2) by a rounding unit at a .005 boundary — same pattern as
    # explain_cell's response. A tolerance, not exact equality, is the honest check here.
    assert result["deviation"] == pytest.approx(result["lst_mean"] - result["city_mean"], abs=0.02)


def test_explain_ward_unknown_ward_is_a_labelled_error(toolbelt):
    result = toolbelt["explain_ward"].invoke({"ward_code": "ZZ"})
    assert result["error_code"] == "ward_not_found"


def test_simulate_scenario_greening_only_cools(toolbelt):
    result = toolbelt["simulate_scenario"].invoke(
        {"ward_code": KNOWN_LAND_WARD, "intervention": "greening", "coverage": 1.0}
    )
    assert result["mean_dlst"] <= 0
    assert isinstance(result["clamped"], bool)


def test_simulate_scenario_unknown_ward_is_a_labelled_error(toolbelt):
    result = toolbelt["simulate_scenario"].invoke({"ward_code": "ZZ", "intervention": "greening"})
    assert result["error_code"] == "ward_not_found"


def test_get_weather_uses_mocked_upstream(toolbelt, monkeypatch):
    fake_daily = {
        "time": ["2026-07-26"],
        "temperature_2m_max": [32.1],
        "temperature_2m_min": [26.0],
        "relative_humidity_2m_mean": [78.0],
        "wind_speed_10m_max": [4.2],
        "precipitation_sum": [0.0],
    }
    monkeypatch.setattr("backend.services._fetch_weather", lambda days: {"daily": fake_daily})
    result = toolbelt["get_weather"].invoke({"days": 1})
    assert result["source"] == "open-meteo"
    assert len(result["days"]) == 1


def test_get_trend_is_an_honest_stub(toolbelt):
    result = toolbelt["get_trend"].invoke({})
    assert result["available"] is False
