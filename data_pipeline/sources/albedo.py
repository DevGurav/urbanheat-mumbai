"""Landsat broadband surface albedo (Liang 2001), one row per grid cell.

Produces `data/interim/albedo.parquet`: `albedo`, the fraction of incoming shortwave
radiation a surface reflects (0–1). This is the **cool-roof lever** — the scenario engine
raises a cell's albedo (reflective roofs) and re-predicts LST, so it must be a real physical
quantity, not an index.

Reuses the Landsat dry-season collection and cloud mask from `landsat.py`, so albedo and LST
composite over identical scenes.

Run standalone with:

    uv run python -m data_pipeline.sources.albedo --limit 200   # smoke test
    uv run python -m data_pipeline.sources.albedo               # full grid
"""

from __future__ import annotations

import argparse

import ee
import geopandas as gpd
import pandas as pd

from data_pipeline.config import get_settings
from data_pipeline.ee_session import init as ee_init
from data_pipeline.sources._reduce import reduce_to_cells, study_region
from data_pipeline.sources.landsat import (
    SR_OFFSET,
    SR_SCALE,
    cloud_mask,
    dry_season_collection,
)

# Optical surface reflectance is 30 m native.
REDUCE_SCALE_M = 30

# Liang (2001) narrowband→broadband total shortwave albedo. The ETM+ bands 1,3,4,5,7 of the
# original paper map to Landsat 8/9 OLI SR_B2, SR_B4, SR_B5, SR_B6, SR_B7 (blue, red, NIR,
# SWIR1, SWIR2). Published coefficients, used directly (they sum to 1.016 — a perfect
# reflector returns ~1). Validated at known surfaces: sea ~0.03, forest ~0.12, apron ~0.15.
LIANG = "0.356*B2 + 0.130*B4 + 0.373*B5 + 0.085*B6 + 0.072*B7 - 0.0018"
LIANG_BANDS = ["SR_B2", "SR_B4", "SR_B5", "SR_B6", "SR_B7"]


def albedo_of(image: ee.Image) -> ee.Image:
    """Broadband albedo of one scene, cloud-masked."""
    sr = image.select(LIANG_BANDS).multiply(SR_SCALE).add(SR_OFFSET)
    albedo = sr.expression(
        LIANG,
        {b.split("_")[1]: sr.select(b) for b in LIANG_BANDS},
    ).rename("albedo")
    return albedo.updateMask(cloud_mask(image)).copyProperties(image, ["system:time_start"])


def build(*, limit: int | None = None, write: bool = True) -> pd.DataFrame:
    """Reduce dry-season broadband albedo to one row per grid cell."""
    settings = get_settings()
    project = ee_init()
    print(f"[albedo] Earth Engine ready — project {project}")

    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet")
    if limit is not None:
        grid = grid.head(limit)
        print(f"[albedo] SMOKE TEST — first {len(grid):,} cells only, not writing output")

    region = study_region(settings)
    collection = dry_season_collection(region)
    n_scenes = int(collection.size().getInfo())
    print(f"[albedo] {n_scenes} scenes over Mumbai, Mar–May")
    if not 0 < n_scenes < 1000:
        raise RuntimeError(f"{n_scenes} scenes — filterBounds/date filters are wrong")

    # Median over the dry-season albedo stack, matching the LST compositing.
    composite = ee.ImageCollection(collection.map(albedo_of)).median()

    print(f"[albedo] reducing over {len(grid):,} cells at {REDUCE_SCALE_M} m")
    # Single-band image → reduceRegions names the mean output "mean", after the reducer, not
    # the band (multi-band images name after the bands). Same quirk as WorldPop's "sum".
    alb = reduce_to_cells(composite, grid, ["mean"], scale=REDUCE_SCALE_M, label="albedo")
    alb = alb.rename(columns={"mean": "albedo"})

    alb = grid[["cell_id"]].merge(alb, on="cell_id", how="left")
    _report(alb, grid)

    if write and limit is None:
        dest = settings.interim_dir / "albedo.parquet"
        alb.to_parquet(dest, index=False)
        print(f"[albedo] wrote {dest}")

    return alb


def _report(alb: pd.DataFrame, grid: gpd.GeoDataFrame) -> None:
    """Print the checks that would catch a silently wrong reduction."""
    if len(alb) != len(grid):
        raise ValueError(f"row count {len(alb):,} != grid {len(grid):,}")
    if alb["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id in the reduction output")

    a = alb["albedo"].dropna()
    missing = int(alb["albedo"].isna().sum())
    print(f"[albedo] {len(alb):,} rows, {missing:,} with no albedo")
    print(f"[albedo]   albedo  min {a.min():.3f}  median {a.median():.3f}  max {a.max():.3f}")

    # Albedo is a reflectance fraction: physically in [0, 1], and for a snow-free tropical
    # city realistically ~0.02 (water) to ~0.35 (bright roofs/bare). Outside that means the
    # band scaling or the coefficients are wrong.
    if a.min() < 0 or a.max() > 1:
        raise ValueError(f"albedo out of [0, 1]: [{a.min():.3f}, {a.max():.3f}]")
    if a.max() > 0.5:
        raise ValueError(
            f"albedo max {a.max():.3f} is too bright for snow-free Mumbai — check scaling"
        )


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
