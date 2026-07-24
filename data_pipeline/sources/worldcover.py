"""ESA WorldCover land-cover fractions, one row per grid cell.

Produces `data/interim/worldcover.parquet`: the share of each cell in each land-cover class.
WorldCover v200 is a single static 10 m mosaic (2021), so there is no temporal stack and no
cloud masking — the reduction is a per-class pixel count via a frequency histogram.

The class list is wider than the data-dictionary's original tree/grass/built plan, because
inspection showed Mumbai's greenest cells are mangrove (95) and a lot of dry ground reads as
cropland (40) — both material here and neither captured by the original three.

Run standalone with:

    uv run python -m data_pipeline.sources.worldcover --limit 200   # smoke test
    uv run python -m data_pipeline.sources.worldcover               # full grid
"""

from __future__ import annotations

import argparse

import ee
import geopandas as gpd
import pandas as pd

from data_pipeline.config import get_settings
from data_pipeline.ee_session import init as ee_init
from data_pipeline.sources._reduce import reduce_to_cells

# WorldCover v200 native resolution. Class labels are categorical — they must be counted at
# native scale, never resampled to a coarser one (that would interpolate class codes). A
# single static image makes 10 m cheap here, unlike the multi-scene optical stacks.
REDUCE_SCALE_M = 10

# WorldCover code → output column stem. Snow (70) and moss (100) never occur in Mumbai and
# are dropped; every other class is kept so the fractions sum to ~1 and stay auditable.
CLASSES = {
    10: "tree",
    20: "shrub",
    30: "grass",
    40: "crop",
    50: "built",
    60: "bare",
    80: "water",
    90: "wetland",
    95: "mangrove",
}


def worldcover_image() -> ee.Image:
    """The 2021 v200 land-cover mosaic, `Map` band only."""
    return ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")


def _expand_histograms(raw: pd.DataFrame) -> pd.DataFrame:
    """Turn the per-cell class histogram into one fraction column per class.

    `reduceRegions` with a frequency-histogram reducer returns the counts as a dict in the
    `histogram` property (named after the reducer, not the band). Counts are partial-pixel
    weighted, so they are fractional. The denominator is the cell's total classified pixels
    (≈ the full cell, since the sea is class 80 rather than masked), so the fractions are
    share-of-cell and sum to 1 — which `_report` checks.
    """
    rows = []
    for cell_id, hist in zip(raw["cell_id"], raw["histogram"], strict=True):
        hist = hist or {}
        total = sum(hist.values())
        row: dict = {"cell_id": cell_id, "wc_pixels": round(total, 1)}
        for code, name in CLASSES.items():
            row[f"{name}_fraction"] = (hist.get(str(code), 0) / total) if total else None
        rows.append(row)
    return pd.DataFrame(rows)


def build(*, limit: int | None = None, write: bool = True) -> pd.DataFrame:
    """Reduce WorldCover to per-class fractions, one row per grid cell."""
    settings = get_settings()
    project = ee_init()
    print(f"[worldcover] Earth Engine ready — project {project}")

    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet")
    if limit is not None:
        grid = grid.head(limit)
        print(f"[worldcover] SMOKE TEST — first {len(grid):,} cells only, not writing output")

    print(f"[worldcover] reducing over {len(grid):,} cells at {REDUCE_SCALE_M} m")
    raw = reduce_to_cells(
        worldcover_image(),
        grid,
        ["histogram"],  # frequencyHistogram names its output after the reducer, not the band
        scale=REDUCE_SCALE_M,
        label="worldcover",
        reducer=ee.Reducer.frequencyHistogram(),
    )

    wc = _expand_histograms(raw)
    wc = grid[["cell_id"]].merge(wc, on="cell_id", how="left")
    _report(wc, grid)

    if write and limit is None:
        dest = settings.interim_dir / "worldcover.parquet"
        wc.to_parquet(dest, index=False)
        print(f"[worldcover] wrote {dest}")

    return wc


def _report(wc: pd.DataFrame, grid: gpd.GeoDataFrame) -> None:
    """Print the checks that would catch a silently wrong reduction."""
    if len(wc) != len(grid):
        raise ValueError(f"row count {len(wc):,} != grid {len(grid):,}")
    if wc["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id in the reduction output")

    frac_cols = [f"{name}_fraction" for name in CLASSES.values()]
    missing = int(wc[frac_cols[0]].isna().sum())
    print(f"[worldcover] {len(wc):,} rows, {missing:,} with no land cover")

    valid = wc.dropna(subset=frac_cols)
    if valid.empty:
        raise ValueError("every cell came back empty — the reduction produced nothing")

    # Every kept class sums with the others to ~1 (snow/moss are the only omitted classes and
    # do not occur here). A sum far from 1 means a class was dropped that should not have been.
    totals = valid[frac_cols].sum(axis=1)
    if not ((totals > 0.98) & (totals < 1.02)).all():
        raise ValueError(
            f"class fractions do not sum to 1: range [{totals.min():.3f}, {totals.max():.3f}] "
            "— a non-trivial class is being dropped"
        )

    print("[worldcover] city-wide mean composition:")
    for name in CLASSES.values():
        share = valid[f"{name}_fraction"].mean()
        if share >= 0.005:
            print(f"[worldcover]   {name:9} {share:6.1%}")


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
