"""Sentinel-2 vegetation, built-up and water indices, one row per grid cell.

Produces `data/interim/sentinel2.parquet`: `ndvi_mean`, `ndvi_p10`, `ndbi_mean`,
`ndwi_mean` (data-dictionary §3). NDVI is the primary cooling driver; NDBI the primary
warming driver. Dry-season Mar–May composites, matching the LST target's years.

Run standalone with:

    uv run python -m data_pipeline.sources.sentinel2 --limit 200   # smoke test
    uv run python -m data_pipeline.sources.sentinel2               # full grid
"""

from __future__ import annotations

import argparse

import ee
import geopandas as gpd
import pandas as pd

from data_pipeline.config import get_settings
from data_pipeline.ee_session import init as ee_init
from data_pipeline.sources._reduce import reduce_to_cells, study_region

START_YEAR, END_YEAR = 2019, 2026
DRY_SEASON = (3, 5)
MAX_SCENE_CLOUD = 40  # percent; scene-level pre-filter, per-pixel SCL mask does the real work

# Bands are 10 m (B3/B4/B8) and 20 m (B11). The output is a 200 m cell *mean*, which is
# insensitive to sampling finer than ~50 m for a spatially smooth field like NDVI, so 30 m
# (~44 samples/cell) gives the same cell mean as 20 m at roughly half the server cost.
# Measured: 20 m ran ~70 s per 200 cells (~70 min full grid); 30 m brings that in range.
REDUCE_SCALE_M = 30

# Scene Classification Layer values to reject: 0 no-data, 1 saturated/defective, 3 cloud
# shadow, 8 cloud medium prob, 9 cloud high prob, 10 thin cirrus, 11 snow. Water (6) is
# kept — like the LST stage, water is a real surface, not an error.
BAD_SCL = [0, 1, 3, 8, 9, 10, 11]


def mask_and_index(image: ee.Image) -> ee.Image:
    """Mask cloud/shadow via SCL and return the three normalised-difference indices.

    Normalised differences are computed on the harmonised DN directly. `S2_SR_HARMONIZED`
    removes the post-2022 processing-baseline offset, so a single band offset applies to all
    bands and does not need scaling out before the ratio — but the *harmonisation* is what
    makes that true, which is why this collection is used rather than plain `S2_SR`.
    """
    scl = image.select("SCL")
    keep = scl.remap(BAD_SCL, [0] * len(BAD_SCL), 1)  # bad classes → 0, everything else → 1

    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")  # (NIR−Red)/(NIR+Red)
    ndbi = image.normalizedDifference(["B11", "B8"]).rename("ndbi")  # (SWIR−NIR)/(SWIR+NIR)
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("ndwi")  # (Green−NIR)/(Green+NIR)

    return (
        ee.Image.cat([ndvi, ndbi, ndwi])
        .updateMask(keep)
        .copyProperties(image, ["system:time_start"])
    )


def build_composite(region: ee.Geometry) -> tuple[ee.Image, int]:
    """Four-band index composite over the dry-season stack. Returns (image, scene count)."""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(f"{START_YEAR}-01-01", f"{END_YEAR + 1}-01-01")
        .filter(ee.Filter.calendarRange(DRY_SEASON[0], DRY_SEASON[1], "month"))
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_SCENE_CLOUD))
    )

    indexed = ee.ImageCollection(collection.map(mask_and_index))

    composite = ee.Image.cat(
        [
            indexed.select("ndvi").median().rename("ndvi_mean"),
            # 10th percentile — worst-case greenness, the dry-year low the median hides.
            indexed.select("ndvi").reduce(ee.Reducer.percentile([10])).rename("ndvi_p10"),
            indexed.select("ndbi").median().rename("ndbi_mean"),
            indexed.select("ndwi").median().rename("ndwi_mean"),
        ]
    )
    return composite, int(collection.size().getInfo())


def build(*, limit: int | None = None, write: bool = True) -> pd.DataFrame:
    """Reduce dry-season Sentinel-2 indices to one row per grid cell."""
    settings = get_settings()
    project = ee_init()
    print(f"[sentinel2] Earth Engine ready — project {project}")

    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet")
    if limit is not None:
        grid = grid.head(limit)
        print(f"[sentinel2] SMOKE TEST — first {len(grid):,} cells only, not writing output")

    region = study_region(settings)
    composite, n_scenes = build_composite(region)
    print(f"[sentinel2] {n_scenes} scenes over Mumbai, Mar–May {START_YEAR}–{END_YEAR}")
    if n_scenes == 0:
        raise RuntimeError("no scenes matched — check the date and cloud filters")

    bands = ["ndvi_mean", "ndvi_p10", "ndbi_mean", "ndwi_mean"]
    print(f"[sentinel2] reducing over {len(grid):,} cells at {REDUCE_SCALE_M} m")
    s2 = reduce_to_cells(composite, grid, bands, scale=REDUCE_SCALE_M, label="sentinel2")

    s2 = grid[["cell_id"]].merge(s2, on="cell_id", how="left")
    _report(s2, grid)

    if write and limit is None:
        dest = settings.interim_dir / "sentinel2.parquet"
        s2.to_parquet(dest, index=False)
        print(f"[sentinel2] wrote {dest}")

    return s2


def _report(s2: pd.DataFrame, grid: gpd.GeoDataFrame) -> None:
    """Print the checks that would catch a silently wrong reduction."""
    if len(s2) != len(grid):
        raise ValueError(f"row count {len(s2):,} != grid {len(grid):,}")
    if s2["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id in the reduction output")

    missing = int(s2["ndvi_mean"].isna().sum())
    print(f"[sentinel2] {len(s2):,} rows, {missing:,} with no NDVI ({missing / len(s2):.2%})")

    valid = s2.dropna(subset=["ndvi_mean"])
    if valid.empty:
        raise ValueError("every cell came back empty — the reduction produced nothing")

    for column in ("ndvi_mean", "ndvi_p10", "ndbi_mean", "ndwi_mean"):
        series = valid[column]
        print(
            f"[sentinel2]   {column:<10} min {series.min():+.3f}  "
            f"mean {series.mean():+.3f}  max {series.max():+.3f}"
        )

    # Every index is a normalised difference, so it must lie in [-1, 1]. A value outside
    # that means the band math or the composite is wrong.
    for column in ("ndvi_mean", "ndvi_p10", "ndbi_mean", "ndwi_mean"):
        lo, hi = valid[column].min(), valid[column].max()
        if lo < -1.001 or hi > 1.001:
            raise ValueError(f"{column} out of [-1, 1]: [{lo:.3f}, {hi:.3f}] — check band math")

    # Worst-case greenness cannot exceed the median greenness in any cell.
    bad = int((valid["ndvi_p10"] > valid["ndvi_mean"] + 1e-6).sum())
    if bad:
        raise ValueError(f"{bad} cells have ndvi_p10 > ndvi_mean — percentile wired backwards")


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
