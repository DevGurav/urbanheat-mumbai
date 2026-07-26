"""Build the model's X, y and CV groups from `features.parquet` (ADR-0008).

Applies the training filter and drops every column that must not reach the model — target
leakage, absolute location, and one perfectly-redundant column — so what remains in X is a
legitimate physical predictor.
"""

from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import pandas as pd

from data_pipeline.config import get_settings

TARGET = "lst_mean"
GROUP_COL = "ward_code"  # the spatial CV group — held out whole, never a feature (ADR-0008)
TRAIN_MIN_LAND = 0.5  # cells that are mostly sea carry water temperature, not urban heat

# Non-feature columns, grouped by *why* each is excluded (ADR-0008).
_IDENTITY = ["cell_id", "grid_row", "grid_col", "geometry"]
_LOCATION = ["ward_code", "centroid_lat", "centroid_lon"]  # absolute position → memorisation
_LEAKAGE = ["lst_p90", "lst_obs_count", "wc_pixels"]  # from the target's thermal band, or QA
_REDUNDANT = ["population"]  # exactly 25 × pop_density (a constant cell area) — perfectly collinear
# `land_fraction` is deliberately KEPT: a real geographic property (how coastal a cell is),
# neither absolute location nor leakage. Documented call, per the kickoff.
EXCLUDED = frozenset(_IDENTITY + _LOCATION + _LEAKAGE + _REDUNDANT + [TARGET])


@dataclass(frozen=True)
class ModelData:
    """The modelling inputs, kept together so callers can't misalign X, y and groups."""

    X: pd.DataFrame
    y: pd.Series
    groups: pd.Series
    feature_names: list[str]


def load_features() -> gpd.GeoDataFrame:
    return gpd.read_parquet(get_settings().processed_dir / "features.parquet")


def build_dataset(
    *, min_land: float = TRAIN_MIN_LAND, frame: pd.DataFrame | None = None
) -> ModelData:
    """X, y and ward groups for the model. `frame` overrides the parquet (used in tests)."""
    df = load_features() if frame is None else frame
    train = df[df["land_fraction"] >= min_land].reset_index(drop=True)

    feature_names = [c for c in train.columns if c not in EXCLUDED]

    # Belt-and-braces: nothing excluded may reach X, and X must be complete.
    leaked = EXCLUDED & set(feature_names)
    if leaked:
        raise AssertionError(f"excluded columns leaked into X: {sorted(leaked)}")
    X = train[feature_names].copy()
    if X.isna().any().any():
        raise ValueError(f"NaNs in features: {X.columns[X.isna().any()].tolist()}")

    y = train[TARGET].copy()
    groups = train[GROUP_COL].copy()

    print(
        f"[dataset] {len(train):,} cells (land_fraction >= {min_land}), "
        f"{len(feature_names)} features, target={TARGET}, {groups.nunique()} ward groups"
    )
    return ModelData(X=X, y=y, groups=groups, feature_names=feature_names)
