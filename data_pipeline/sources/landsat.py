"""Landsat 8/9 surface temperature, reduced to one row per grid cell.

Promotes the Phase 0 notebook logic (`notebooks/00_hello_earth_engine.ipynb`) into the
pipeline and adds the per-cell reduction. Produces `data/interim/lst.parquet` with the
target variable.

Run standalone with:

    uv run python -m data_pipeline.sources.landsat --limit 200   # smoke test
    uv run python -m data_pipeline.sources.landsat               # full grid
"""

from __future__ import annotations

import argparse
import time

import ee
import geopandas as gpd
import pandas as pd

from data_pipeline.config import get_settings
from data_pipeline.ee_session import init as ee_init

# --- Collection 2 Level-2 scaling constants (USGS Data Format Control Book) ---
ST_SCALE, ST_OFFSET = 0.00341802, 149.0  # ST_B10 → Kelvin
KELVIN_TO_C = 273.15

# QA_PIXEL bits to reject. Water (7) is deliberately kept — the sea and the lakes are
# genuine cool surfaces, not errors. Rationale for each bit is in the Phase 0 notebook §3.2.
CLOUD_BITS = (1, 2, 3, 4)  # dilated cloud, cirrus, cloud, cloud shadow

START_YEAR, END_YEAR = 2019, 2026
DRY_SEASON = (3, 5)  # Mar–May. Monsoon imagery is unusable (ADR-0005)
MAX_SCENE_CLOUD = 40  # percent; scene-level pre-filter only

# Native thermal resolution. Asking for 30 m would only interpolate the same information
# at four times the cost.
REDUCE_SCALE_M = 100

# reduceRegions is server-side, but the *result* still has to come down through getInfo.
# One call over all ~12k cells exceeds the payload limit, so cells go up in batches. This
# is not the per-cell getInfo loop ADR-0001 forbids — it is ~24 requests, each returning a
# fully reduced table, which is exactly the "export aggregates" pattern that ADR requires.
CHUNK_SIZE = 500


def prepare(image: ee.Image) -> ee.Image:
    """Scale one scene's thermal band to °C and mask cloud-affected pixels."""
    qa = image.select("QA_PIXEL")
    clear = qa.bitwiseAnd(1 << CLOUD_BITS[0]).eq(0)
    for bit in CLOUD_BITS[1:]:
        clear = clear.And(qa.bitwiseAnd(1 << bit).eq(0))

    kelvin = image.select("ST_B10").multiply(ST_SCALE).add(ST_OFFSET)
    lst = kelvin.subtract(KELVIN_TO_C).rename("LST")

    return lst.updateMask(clear).copyProperties(image, ["system:time_start"])


def build_composite(region: ee.Geometry) -> tuple[ee.Image, int]:
    """Three-band composite over the dry-season stack. Returns (image, scene count).

    `region` is not optional. Without `filterBounds` the collection is the *global* archive
    — ~349k scenes rather than Mumbai's ~60. Earth Engine's laziness means the reduced
    values come out the same either way, which is exactly what makes the omission
    dangerous: the only visible symptom is a scene count nobody checks.
    """
    collection = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2"))
        .filterBounds(region)
        .filterDate(f"{START_YEAR}-01-01", f"{END_YEAR + 1}-01-01")
        .filter(ee.Filter.calendarRange(DRY_SEASON[0], DRY_SEASON[1], "month"))
        .filter(ee.Filter.lt("CLOUD_COVER", MAX_SCENE_CLOUD))
    )

    stack = ee.ImageCollection(collection.map(prepare)).select("LST")

    # Median, not mean: it resists the handful of cloud pixels the QA mask inevitably
    # misses. One missed −20 °C cloud top visibly drags a mean and barely moves a median.
    composite = ee.Image.cat(
        [
            stack.median().rename("lst_median"),
            # Temporal 90th percentile — the hot extreme the median hides, per
            # data-dictionary §2. Not a spatial percentile within the cell.
            stack.reduce(ee.Reducer.percentile([90])).rename("lst_p90"),
            # Cloud-free observations per pixel. A cell composited from three scenes is
            # far less trustworthy than one composited from forty, and without this column
            # that difference is invisible in the feature table.
            stack.count().rename("lst_obs_count"),
        ]
    )
    return composite, int(collection.size().getInfo())


def _cells_to_features(chunk: gpd.GeoDataFrame) -> ee.FeatureCollection:
    """Convert a chunk of grid cells to an Earth Engine FeatureCollection.

    Cells go up as explicit polygons with `geodesic=False`: they were built as squares in
    EPSG:32643, so their edges are straight in projection, not great-circle arcs. Letting
    Earth Engine assume geodesic edges would bow them very slightly outward.
    """
    features = []
    for cell_id, geom in zip(chunk["cell_id"], chunk.geometry, strict=True):
        coords = [list(xy) for xy in geom.exterior.coords]
        features.append(
            ee.Feature(
                ee.Geometry.Polygon(coords, proj="EPSG:4326", geodesic=False),
                {"cell_id": int(cell_id)},
            )
        )
    return ee.FeatureCollection(features)


def reduce_to_cells(composite: ee.Image, grid: gpd.GeoDataFrame) -> pd.DataFrame:
    """Reduce the composite over every grid cell, in chunks."""
    rows: list[dict] = []
    n_chunks = (len(grid) + CHUNK_SIZE - 1) // CHUNK_SIZE
    started = time.time()

    for i in range(n_chunks):
        chunk = grid.iloc[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
        reduced = composite.reduceRegions(
            collection=_cells_to_features(chunk),
            reducer=ee.Reducer.mean(),
            scale=REDUCE_SCALE_M,
            # Splits the work into smaller tiles when a chunk would otherwise exceed the
            # per-request memory limit. Slower, but it does not fail at 500 cells a time.
            tileScale=4,
        )

        # One getInfo per chunk, each returning an already-reduced table.
        for feature in reduced.getInfo()["features"]:
            props = feature["properties"]
            rows.append(
                {
                    "cell_id": props["cell_id"],
                    "lst_mean": props.get("lst_median"),
                    "lst_p90": props.get("lst_p90"),
                    "lst_obs_count": props.get("lst_obs_count"),
                }
            )

        elapsed = time.time() - started
        done = i + 1
        eta = elapsed / done * (n_chunks - done)
        print(
            f"[landsat]   chunk {done}/{n_chunks}  {len(rows):,} cells  "
            f"{elapsed:,.0f}s elapsed, ~{eta:,.0f}s left",
            flush=True,
        )

    return pd.DataFrame(rows)


def build(*, limit: int | None = None, write: bool = True) -> pd.DataFrame:
    """Reduce dry-season LST to one row per grid cell."""
    settings = get_settings()
    project = ee_init()
    print(f"[landsat] Earth Engine ready — project {project}")

    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet")
    if limit is not None:
        grid = grid.head(limit)
        print(f"[landsat] SMOKE TEST — first {len(grid):,} cells only, not writing output")

    # Always the *full* grid's extent, never the limited subset: a smoke test must exercise
    # the same collection the real run does, or it is not testing the real run.
    full_bounds = gpd.read_parquet(settings.interim_dir / "grid.parquet").total_bounds
    region = ee.Geometry.Rectangle(
        [float(b) for b in full_bounds], proj="EPSG:4326", geodesic=False
    )

    composite, n_scenes = build_composite(region)
    print(f"[landsat] {n_scenes} scenes over Mumbai, Mar–May {START_YEAR}–{END_YEAR}")
    if n_scenes == 0:
        raise RuntimeError("no scenes matched — check the date and cloud filters")
    if n_scenes > 1000:
        raise RuntimeError(
            f"{n_scenes:,} scenes is far too many for one city — filterBounds is not working"
        )

    print(f"[landsat] reducing over {len(grid):,} cells at {REDUCE_SCALE_M} m")
    lst = reduce_to_cells(composite, grid)

    lst = grid[["cell_id"]].merge(lst, on="cell_id", how="left")
    _report(lst, grid)

    if write and limit is None:
        dest = settings.interim_dir / "lst.parquet"
        lst.to_parquet(dest, index=False)
        print(f"[landsat] wrote {dest}")

    return lst


def _report(lst: pd.DataFrame, grid: gpd.GeoDataFrame) -> None:
    """Print the checks that would catch a silently wrong reduction."""
    if len(lst) != len(grid):
        raise ValueError(f"row count {len(lst):,} != grid {len(grid):,}")
    if lst["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id in the reduction output")

    missing = int(lst["lst_mean"].isna().sum())
    print(f"[landsat] {len(lst):,} rows, {missing:,} with no LST ({missing / len(lst):.2%})")

    valid = lst.dropna(subset=["lst_mean"])
    if valid.empty:
        raise ValueError("every cell came back empty — the reduction produced nothing")

    for column in ("lst_mean", "lst_p90"):
        series = valid[column]
        print(
            f"[landsat]   {column:<14} min {series.min():5.1f}  "
            f"mean {series.mean():5.1f}  max {series.max():5.1f} °C"
        )

    obs = valid["lst_obs_count"]
    print(
        f"[landsat]   observations   min {obs.min():5.1f}  "
        f"mean {obs.mean():5.1f}  max {obs.max():5.1f}"
    )
    for threshold in (5, 10, 20):
        n = int((obs < threshold).sum())
        print(f"[landsat]     < {threshold:>2} obs  {n:>6,}  ({n / len(valid):>5.1%})")

    # Physical floor: the target is a dry-season mid-morning surface in a tropical city.
    # Anything below 15 °C means the scaling or the masking is wrong, not that Mumbai is
    # cold — this is the "values around 300" class of bug caught before it reaches a model.
    if valid["lst_mean"].min() < 15:
        raise ValueError(f"implausible minimum {valid['lst_mean'].min():.1f} °C — check scaling")
    if valid["lst_mean"].max() > 70:
        raise ValueError(f"implausible maximum {valid['lst_mean'].max():.1f} °C — check scaling")


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
