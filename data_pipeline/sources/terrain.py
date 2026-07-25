"""Terrain and distance context, one row per grid cell.

Produces `data/interim/terrain.parquet`: `elevation_mean`, `slope_mean`, `dist_coast`,
`dist_water`. Elevation/slope come from SRTM; the distances are surface-spread distances to
the sea and to any permanent water. Distance-to-coast is expected to matter in Mumbai — the
sea breeze cools the shore.

Distances use `cumulativeCost` (metres directly, robust to scale) rather than
`fastDistanceTransform`, whose pixel-unit output inflated far distances in testing.

Run standalone with:

    uv run python -m data_pipeline.sources.terrain --limit 200   # smoke test
    uv run python -m data_pipeline.sources.terrain               # full grid
"""

from __future__ import annotations

import argparse

import ee
import geopandas as gpd
import pandas as pd

from data_pipeline.config import get_settings
from data_pipeline.ee_session import init as ee_init
from data_pipeline.sources._reduce import reduce_to_cells

# Elevation/slope reduced at SRTM native 30 m. Distances are computed on a 100 m UTM grid —
# fine for a 200 m cell, and cumulativeCost over a finer grid is far more expensive.
REDUCE_SCALE_M = 30
DIST_SCALE_M = 100  # UTM 43N grid the distances are computed on
MAX_DIST_M = 25000  # caps the spread; Mumbai's deepest interior is ~9 km from the sea

# JRC permanent-water threshold (occurrence %). Below this is seasonal/transient water.
PERMANENT_WATER_PCT = 80
# A connected water body larger than this (in 100 m pixels) is treated as sea/tidal, not a
# lake: 1024 px = 10.24 km². Powai (2 km²) and Vihar (7 km²) fall under it; the Arabian Sea
# and Thane creek are far above and get capped at it.
SEA_MIN_PIXELS = 1024


def terrain_image() -> ee.Image:
    """Four bands: elevation, slope, distance-to-coast, distance-to-water."""
    # Built here, not at module import, so it runs after Earth Engine is initialised.
    dist_crs = ee.Projection("EPSG:32643").atScale(DIST_SCALE_M)

    srtm = ee.Image("USGS/SRTMGL1_003").select("elevation")
    slope = ee.Terrain.slope(srtm)

    water = (
        ee.Image("JRC/GSW1_4/GlobalSurfaceWater")
        .select("occurrence")
        .gte(PERMANENT_WATER_PCT)
        .unmask(0)
        .reproject(dist_crs)
    )
    conn = water.connectedPixelCount(SEA_MIN_PIXELS, True).reproject(dist_crs)
    sea = water.eq(1).And(conn.gte(SEA_MIN_PIXELS))

    cost = ee.Image(1).reproject(dist_crs)
    dist_coast = cost.cumulativeCost(sea, MAX_DIST_M)
    dist_water = cost.cumulativeCost(water, MAX_DIST_M)

    return ee.Image.cat(
        [
            srtm.rename("elevation_mean"),
            slope.rename("slope_mean"),
            dist_coast.rename("dist_coast"),
            dist_water.rename("dist_water"),
        ]
    )


def build(*, limit: int | None = None, write: bool = True) -> pd.DataFrame:
    """Reduce terrain and distance context to one row per grid cell."""
    settings = get_settings()
    project = ee_init()
    print(f"[terrain] Earth Engine ready — project {project}")

    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet")
    if limit is not None:
        grid = grid.head(limit)
        print(f"[terrain] SMOKE TEST — first {len(grid):,} cells only, not writing output")

    bands = ["elevation_mean", "slope_mean", "dist_coast", "dist_water"]
    print(f"[terrain] reducing over {len(grid):,} cells at {REDUCE_SCALE_M} m")
    terr = reduce_to_cells(terrain_image(), grid, bands, scale=REDUCE_SCALE_M, label="terrain")

    terr = grid[["cell_id"]].merge(terr, on="cell_id", how="left")
    _report(terr, grid)

    if write and limit is None:
        dest = settings.interim_dir / "terrain.parquet"
        terr.to_parquet(dest, index=False)
        print(f"[terrain] wrote {dest}")

    return terr


def _report(terr: pd.DataFrame, grid: gpd.GeoDataFrame) -> None:
    """Print the checks that would catch a silently wrong reduction."""
    if len(terr) != len(grid):
        raise ValueError(f"row count {len(terr):,} != grid {len(grid):,}")
    if terr["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id in the reduction output")

    for col in ("elevation_mean", "slope_mean", "dist_coast", "dist_water"):
        s = terr[col].dropna()
        print(
            f"[terrain]   {col:<14} min {s.min():7.1f}  "
            f"median {s.median():7.1f}  max {s.max():7.1f}"
        )

    # SRTM over Greater Mumbai: sea level to the SGNP hills (~450 m). A negative floor beyond
    # a metre or two of coastal noise, or a max far above 500 m, means the wrong DEM or scale.
    elev = terr["elevation_mean"].dropna()
    if elev.min() < -10 or elev.max() > 600:
        raise ValueError(f"elevation range [{elev.min():.0f}, {elev.max():.0f}] m is not Mumbai")
    # Distances are capped at MAX_DIST_M; a whole column pinned there means the spread failed.
    if terr["dist_coast"].median() > MAX_DIST_M * 0.8:
        raise ValueError("dist_coast median near the cap — the sea mask or cumulativeCost failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="reduce only the first N cells and skip writing — for smoke tests",
    )
    args = parser.parse_args()
    build(limit=args.limit)
