"""Assemble the feature table — the artifact everything downstream reads (ADR-0004).

Joins every per-source interim table and the LST target on `cell_id`, derives the
neighbourhood and impervious composites, validates, and writes
`data/processed/features.parquet` (GeoParquet — geometry travels with the table so the API
and notebooks read one file).

The validation gate is the point of this stage. A silent join failure across 12k cells has
no printed area to catch it (the Phase 0 boundary lesson), so every column is asserted on
row count, null rate and physical range — counts *and* magnitudes, never just non-emptiness.

Run standalone with:

    uv run python -m data_pipeline.assemble
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from data_pipeline.config import get_settings

# Each interim table → the columns it contributes (everything except its cell_id key).
SOURCES = {
    "lst": ["lst_mean", "lst_p90", "lst_obs_count"],
    "sentinel2": ["ndvi_mean", "ndvi_p10", "ndbi_mean", "ndwi_mean"],
    "worldcover": [
        "tree_fraction",
        "shrub_fraction",
        "grass_fraction",
        "crop_fraction",
        "built_fraction",
        "bare_fraction",
        "water_fraction",
        "wetland_fraction",
        "mangrove_fraction",
        "wc_pixels",
    ],
    "worldpop": ["population", "pop_density"],
    "terrain": ["elevation_mean", "slope_mean", "dist_coast", "dist_water"],
    "osm": ["building_count", "building_density", "road_density", "dist_park"],
    "albedo": ["albedo"],
    "weather": ["air_temp_mean", "humidity_mean", "wind_speed_mean"],
}

# Typical carriageway width (m) for the OSM drive network, to turn road *length* density
# (m/m²) into a road *area* fraction for the impervious composite. A stated assumption.
ROAD_WIDTH_M = 8.0

# Physical bounds per column: assertion fails outside, so a broken join or unit error stops
# here rather than reaching the model. Fractions are 0–1; indices −1…1; see data-dictionary.
RANGES = {
    "lst_mean": (15, 70),
    "lst_p90": (15, 75),
    "ndvi_mean": (-1, 1),
    "ndvi_p10": (-1, 1),
    "ndbi_mean": (-1, 1),
    "ndwi_mean": (-1, 1),
    "tree_fraction": (0, 1),
    "built_fraction": (0, 1),
    "water_fraction": (0, 1),
    "mangrove_fraction": (0, 1),
    "crop_fraction": (0, 1),
    "albedo": (0, 0.5),
    "building_density": (0, 1),
    "impervious_fraction": (0, 1),
    "land_fraction": (0, 1),
    "population": (0, 1e5),
    "pop_density": (0, 5e5),
    "elevation_mean": (-10, 600),
    "slope_mean": (0, 60),
    "dist_coast": (0, 25000),
    "dist_water": (0, 25000),
    "dist_park": (0, 25000),
    "ndvi_neigh_mean": (-1, 1),
    "built_neigh_mean": (0, 1),
    "air_temp_mean": (15, 45),
    "humidity_mean": (0, 100),
    "wind_speed_mean": (0, 30),
}

# Columns that must never be null — the target and the load-bearing predictors.
REQUIRED = [
    "lst_mean",
    "ndvi_mean",
    "ndbi_mean",
    "built_fraction",
    "water_fraction",
    "population",
    "elevation_mean",
    "dist_coast",
    "albedo",
    "ward_code",
    "ndvi_neigh_mean",
    "built_neigh_mean",
]

_QUEEN = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def neighbourhood_mean(df: pd.DataFrame, col: str) -> pd.Series:
    """Mean of `col` over the (up to 8) queen-adjacent cells, via the grid_row/col lattice.

    Adjacency is integer arithmetic on the grid indices (ADR-0007), so this needs no spatial
    join. Edge cells average the neighbours that exist; a cell with none falls back to its
    own value rather than a null.
    """
    lookup = df.set_index(["grid_row", "grid_col"])[col]
    rows = df["grid_row"].to_numpy()
    cols = df["grid_col"].to_numpy()
    total = np.zeros(len(df))
    count = np.zeros(len(df))
    for d_row, d_col in _QUEEN:
        vals = lookup.reindex(list(zip(rows + d_row, cols + d_col, strict=True))).to_numpy()
        present = ~np.isnan(vals)
        total[present] += vals[present]
        count += present
    own = df[col].to_numpy()
    return pd.Series(
        np.where(count > 0, total / np.where(count > 0, count, 1), own), index=df.index
    )


def build(*, write: bool = True) -> gpd.GeoDataFrame:
    """Join every source into the feature table and validate it."""
    settings = get_settings()
    interim = settings.interim_dir

    grid = gpd.read_parquet(interim / "grid.parquet")
    print(f"[assemble] base grid: {len(grid):,} cells")

    df: pd.DataFrame = grid
    for name, cols in SOURCES.items():
        source = pd.read_parquet(interim / f"{name}.parquet")[["cell_id", *cols]]
        if len(source) != len(grid):
            raise ValueError(f"{name}: {len(source):,} rows != grid {len(grid):,}")
        df = df.merge(source, on="cell_id", how="left")

    # --- derived composites ---
    df["impervious_fraction"] = (df["built_fraction"] + df["road_density"] * ROAD_WIDTH_M).clip(
        0, 1
    )
    df["ndvi_neigh_mean"] = neighbourhood_mean(df, "ndvi_mean")
    df["built_neigh_mean"] = neighbourhood_mean(df, "built_fraction")

    features = gpd.GeoDataFrame(df, geometry="geometry", crs=grid.crs)
    _validate(features, grid)

    if write:
        dest = settings.processed_dir / "features.parquet"
        features.to_parquet(dest, index=False)
        size_mb = dest.stat().st_size / 1e6
        shape = f"{len(features):,} rows × {features.shape[1]} columns"
        print(f"[assemble] wrote {dest}")
        print(f"[assemble]   {shape}, {size_mb:.1f} MB")

    return features


def _validate(df: gpd.GeoDataFrame, grid: gpd.GeoDataFrame) -> None:
    """The gate: assert the invariants, report the full column summary."""
    if len(df) != len(grid):
        raise ValueError(f"row count {len(df):,} != grid {len(grid):,}")
    if df["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id in the feature table")

    # Required columns must be fully populated — a null here means a source lost cells.
    for col in REQUIRED:
        n_null = int(df[col].isna().sum())
        if n_null:
            raise ValueError(f"{col}: {n_null:,} nulls — a join dropped cells")

    # Physical-range assertions.
    for col, (lo, hi) in RANGES.items():
        s = df[col].dropna()
        if not s.empty and (s.min() < lo - 1e-6 or s.max() > hi + 1e-6):
            raise ValueError(f"{col} range [{s.min():.3f}, {s.max():.3f}] outside [{lo}, {hi}]")

    print(f"[assemble] validation passed — {df.shape[1]} columns")
    feature_cols = [
        c for c in df.columns if c not in ("cell_id", "geometry", "grid_row", "grid_col")
    ]
    print(f"[assemble] {len(feature_cols)} feature/identity columns, target = lst_mean")
    print(f"[assemble]   {'column':<20} {'nulls':>6} {'min':>10} {'max':>10}")
    for col in feature_cols:
        s = df[col]
        nulls = int(s.isna().sum())
        if pd.api.types.is_numeric_dtype(s):
            print(f"[assemble]   {col:<20} {nulls:>6} {s.min():>10.3f} {s.max():>10.3f}")
        else:
            summary = f"({s.nunique()} categories)"
            print(f"[assemble]   {col:<20} {nulls:>6} {summary:>21}")


if __name__ == "__main__":
    build()
