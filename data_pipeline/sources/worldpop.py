"""WorldPop population, one row per grid cell.

Produces `data/interim/worldpop.parquet`: `population` (persons in the cell) and
`pop_density` (persons/km²). This is the human-exposure layer — the first predictor about
people rather than the physical surface — and it feeds the Heat Vulnerability Index (§ HVI).

WorldPop `GP/100m/pop` stores a *person count* per 100 m pixel, so the cell value is a
**sum**, not a mean. Reduced at native 100 m: summing a count at a coarser scale would
double- or under-count.

Run standalone with:

    uv run python -m data_pipeline.sources.worldpop --limit 200   # smoke test
    uv run python -m data_pipeline.sources.worldpop               # full grid
"""

from __future__ import annotations

import argparse

import ee
import geopandas as gpd
import pandas as pd

from data_pipeline.config import get_settings
from data_pipeline.ee_session import init as ee_init
from data_pipeline.sources._reduce import reduce_to_cells, study_region

# Latest WorldPop year (the collection ends at 2020) — the closest available to the
# 2019–2026 LST window. data-dictionary §5 flagged this alignment as an open question; 2020
# is the honest best match, one year inside the target window.
YEAR = 2020

REDUCE_SCALE_M = 100  # native; a person count must be summed at native resolution
CELL_AREA_KM2 = (200 * 200) / 1e6  # 0.04 km² — the full 200 m cell


def population_image(region: ee.Geometry) -> ee.Image:
    """WorldPop person-count mosaic for `YEAR`, clipped by `region`.

    `mosaic()` collapses any overlapping country/tile images for the year into one surface
    without double-counting (it takes the top pixel, not a sum).
    """
    return (
        ee.ImageCollection("WorldPop/GP/100m/pop")
        .filterBounds(region)
        .filter(ee.Filter.eq("year", YEAR))
        .mosaic()
        .select("population")
    )


def build(*, limit: int | None = None, write: bool = True) -> pd.DataFrame:
    """Reduce WorldPop to population and density, one row per grid cell."""
    settings = get_settings()
    project = ee_init()
    print(f"[worldpop] Earth Engine ready — project {project}")

    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet")
    if limit is not None:
        grid = grid.head(limit)
        print(f"[worldpop] SMOKE TEST — first {len(grid):,} cells only, not writing output")

    region = study_region(settings)
    print(f"[worldpop] reducing WorldPop {YEAR} over {len(grid):,} cells at {REDUCE_SCALE_M} m")
    pop = reduce_to_cells(
        population_image(region),
        grid,
        # Reducer.sum() names its output property "sum", after the reducer, not the band.
        ["sum"],
        scale=REDUCE_SCALE_M,
        label="worldpop",
        reducer=ee.Reducer.sum(),
    )
    pop = pop.rename(columns={"sum": "population"})

    pop = grid[["cell_id"]].merge(pop, on="cell_id", how="left")
    # Cells over open sea are masked in WorldPop → no sum. "No data" here means "no people",
    # so 0 is correct; the total-population reconciliation below guards against a bug that
    # would zero everything.
    pop["population"] = pop["population"].fillna(0.0)
    pop["pop_density"] = pop["population"] / CELL_AREA_KM2

    _report(pop, is_full_grid=limit is None)

    if write and limit is None:
        dest = settings.interim_dir / "worldpop.parquet"
        pop.to_parquet(dest, index=False)
        print(f"[worldpop] wrote {dest}")

    return pop


def _report(pop: pd.DataFrame, *, is_full_grid: bool) -> None:
    """Print the checks that would catch a silently wrong reduction."""
    if pop["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id in the reduction output")
    if (pop["population"] < 0).any():
        raise ValueError("negative population — the sum reducer or the source is wrong")

    total = pop["population"].sum()
    print(f"[worldpop] {len(pop):,} cells, total population {total:,.0f}")
    print(f"[worldpop]   population   max {pop['population'].max():,.0f} in one cell")
    print(
        f"[worldpop]   pop_density  median {pop['pop_density'].median():,.0f}  "
        f"max {pop['pop_density'].max():,.0f} persons/km²"
    )

    # Reconciliation: over the full grid the total must land near Mumbai's known population.
    # A wildly different number means wrong units, wrong year, or a double-counted mosaic.
    # Only meaningful on the full grid — a smoke-test subset covers part of the city.
    if is_full_grid and not (8e6 < total < 16e6):
        raise ValueError(
            f"total population {total:,.0f} is not near Mumbai's ~12 M — check units/year/mosaic"
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
