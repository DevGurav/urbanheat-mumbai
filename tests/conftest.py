"""Shared fixtures.

Pure-logic tests need no data and always run. Data-backed tests depend on the gitignored
`data/processed/*` artifacts and skip cleanly when they haven't been built, so a fresh clone
still gets a green run from the pure-logic suite.
"""

import pytest


@pytest.fixture(scope="session")
def settings():
    try:
        from data_pipeline.config import get_settings

        return get_settings()
    except Exception as exc:  # noqa: BLE001 - a missing .env should skip, not error
        pytest.skip(f"config unavailable (no .env?): {exc}")


@pytest.fixture(scope="session")
def features(settings):
    import geopandas as gpd

    path = settings.processed_dir / "features.parquet"
    if not path.exists():
        pytest.skip("features.parquet not built — run: uv run python -m data_pipeline.assemble")
    return gpd.read_parquet(path)


@pytest.fixture(scope="session")
def wards_gdf(settings):
    import geopandas as gpd

    path = settings.processed_dir / "wards.geojson"
    if not path.exists():
        pytest.skip("wards.geojson not built — run: uv run python -m data_pipeline.boundary")
    return gpd.read_file(path)
