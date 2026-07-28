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


@pytest.fixture(scope="session")
def store():
    """The in-memory artifact store `backend/services.py` and the agent toolbelt read.
    Session-scoped: it's loaded once and never mutated (ADR-0004), so every test in the run
    shares one instance rather than re-reading the parquet files per test.
    """
    from backend.store import load_store

    try:
        return load_store()
    except FileNotFoundError as exc:
        pytest.skip(f"artifacts not built: {exc}")
    except Exception as exc:  # noqa: BLE001 - a missing .env should skip, not error
        if ".env" in str(exc) or "config" in str(exc).lower():
            pytest.skip(str(exc))
        raise


@pytest.fixture(scope="session")
def retriever(settings):
    """The RAG retriever (`backend/rag/retrieve.py`). Session-scoped so the embeddings client
    is built once per test run, not once per test.
    """
    from backend.rag.retrieve import Retriever

    try:
        return Retriever(chroma_dir=settings.chroma_dir)
    except FileNotFoundError as exc:
        pytest.skip(f"Chroma index not built: {exc}")
    except RuntimeError as exc:
        # Retriever now embeds via Gemini's API (ADR-0013), so a missing GEMINI_API_KEY is
        # also a skip, not a fixture error — CI has no .env at all (backend/main.py's
        # lifespan catches the same two exceptions for the same reason).
        pytest.skip(f"GEMINI_API_KEY not set: {exc}")
