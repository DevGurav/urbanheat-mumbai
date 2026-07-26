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


def test_city_grid_returns_geojson(client):
    body = client.get("/city/grid", params={"layer": "lst"}).json()
    assert body["type"] == "FeatureCollection"
    props = body["features"][0]["properties"]
    assert {"cell_id", "ward_code", "value"} <= props.keys()


def test_city_grid_hvi_layer_is_land_only(client):
    all_cells = client.get("/city/grid", params={"layer": "lst"}).json()
    hvi_cells = client.get("/city/grid", params={"layer": "hvi"}).json()
    # hvi.parquet only covers land cells (dataset.TRAIN_MIN_LAND), so it's a strict subset.
    assert len(hvi_cells["features"]) < len(all_cells["features"])


def test_city_grid_rejects_malformed_bbox(client):
    resp = client.get("/city/grid", params={"bbox": "not,a,bbox"})
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "invalid_bbox"


def test_hotspots_ward_ranking_is_sorted_desc(client):
    body = client.get("/hotspots", params={"by": "hvi", "unit": "ward", "n": 5}).json()
    values = [r["value"] for r in body["results"]]
    assert values == sorted(values, reverse=True)
    assert len(body["results"]) == 5


def test_hotspots_cell_ranking_has_top_driver(client):
    body = client.get("/hotspots", params={"by": "lst", "unit": "cell", "n": 3}).json()
    assert all(r["top_driver"] for r in body["results"])


def test_explain_known_land_cell(client):
    # A confirmed land cell with SHAP attribution (data/processed/features.parquet).
    body = client.get("/explain/10453001345").json()
    assert body["measurement"] == "land_surface_temperature"
    assert len(body["drivers"]) == 3
    assert body["deviation"] == round(body["lst_mean"] - body["city_mean"], 2)


def test_explain_unknown_cell_is_404(client):
    resp = client.get("/explain/999999999999")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "cell_not_found"


def test_explain_non_land_cell_is_404_but_distinct(client):
    # A confirmed non-land cell: present in features.parquet, absent from shap_values.parquet.
    resp = client.get("/explain/10452001345")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "cell_not_explained"


def test_predict_known_land_cell(client):
    body = client.get("/predict", params={"cell_id": 10453001345}).json()
    assert body["ward_code"] == "A"
    assert body["residual"] == round(body["observed_lst"] - body["predicted_lst"], 2)
    # The model should land in the right ballpark of the observed value, not just return *a*
    # number — spatial-CV RMSE was ~1.10 °C (model_meta.json), so a few °C is a loose sanity gate.
    assert abs(body["residual"]) < 5.0


def test_predict_non_land_cell_is_404(client):
    resp = client.get("/predict", params={"cell_id": 10452001345})
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "cell_not_predictable"


def test_scenario_greening_cools_and_discloses_clamping(client):
    body = client.post(
        "/scenario", json={"ward_code": "A", "intervention": "greening", "coverage": 1.0}
    ).json()
    assert body["mean_dlst"] <= 0
    assert body["n_cells"] == len(body["cells"])
    assert isinstance(body["clamped"], bool)
    assert body["clamped"] == (body["clamped_cells"] > 0)


def test_scenario_cool_roof_never_clamps(client):
    body = client.post(
        "/scenario", json={"ward_code": "A", "intervention": "cool_roof", "coverage": 0.5}
    ).json()
    assert body["clamped"] is False
    assert body["clamped_cells"] == 0
    assert body["mean_dlst"] <= 0  # cool roofs only cool


def test_scenario_unknown_ward_is_404(client):
    resp = client.post(
        "/scenario", json={"ward_code": "ZZ", "intervention": "greening", "coverage": 1.0}
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "ward_not_found"


def test_trends_is_an_honest_stub(client):
    body = client.get("/trends").json()
    assert body["available"] is False


def test_weather_uses_mocked_upstream(client, monkeypatch):
    fake_daily = {
        "time": ["2026-07-26", "2026-07-27"],
        "temperature_2m_max": [32.1, 31.8],
        "temperature_2m_min": [26.0, 25.9],
        "relative_humidity_2m_mean": [78.0, 80.0],
        "wind_speed_10m_max": [4.2, 3.9],
        "precipitation_sum": [0.0, 2.5],
    }
    monkeypatch.setattr("backend.routers.weather._fetch", lambda days: {"daily": fake_daily})
    body = client.get("/weather", params={"days": 2}).json()
    assert body["source"] == "open-meteo"
    assert len(body["days"]) == 2
    assert body["days"][0]["date"] == "2026-07-26"
