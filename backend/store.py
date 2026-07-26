"""The in-memory artifact store, loaded once at startup (ADR-0004 — files, not a DB).

The whole dataset is a few MB, so the backend holds it in memory and every request reads from
here — no per-request disk or Earth Engine access. A missing artifact fails loudly at startup
with a pointer to the pipeline that builds it.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import joblib
import pandas as pd

from data_pipeline.config import get_settings


@dataclass
class Store:
    """Everything the API serves, held in memory."""

    features: gpd.GeoDataFrame  # one row per cell, with geometry
    hvi: pd.DataFrame  # cell_id → hvi, components, hotspot_rank
    wards: gpd.GeoDataFrame  # 24 ward polygons
    shap: pd.DataFrame  # cell_id → shap_<feature> per feature
    model: object  # the fitted XGBoost regressor
    model_meta: dict  # feature list, metrics, CV scheme
    model_version: str
    data_version: str
    started_at: float

    @property
    def uptime_s(self) -> int:
        return int(time.time() - self.started_at)


def _require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — build it first: `uv run python -m data_pipeline.run --stage all` "
            "then the `data_pipeline.ml` steps (see runbook.md)."
        )
    return path


def load_store() -> Store:
    """Load every artifact from disk. Called once, at app startup."""
    settings = get_settings()
    processed, models = settings.processed_dir, settings.model_dir

    features = gpd.read_parquet(_require(processed / "features.parquet"))
    hvi = pd.read_parquet(_require(processed / "hvi.parquet"))
    wards = gpd.read_file(_require(processed / "wards.geojson"))
    model = joblib.load(_require(models / "model.joblib"))
    model_meta = json.loads(_require(models / "model_meta.json").read_text())
    shap = pd.read_parquet(_require(models / "shap_values.parquet"))

    # Versions: the model name, and the feature table's build date. Both surface at /health so a
    # client can tell which model/data produced a response (an api-reference convention).
    model_version = f"{model_meta.get('model', 'model')}-v1"
    mtime = (processed / "features.parquet").stat().st_mtime
    data_version = datetime.fromtimestamp(mtime, tz=UTC).strftime("%Y%m%d")

    return Store(
        features=features,
        hvi=hvi,
        wards=wards,
        shap=shap,
        model=model,
        model_meta=model_meta,
        model_version=model_version,
        data_version=data_version,
        started_at=time.time(),
    )
