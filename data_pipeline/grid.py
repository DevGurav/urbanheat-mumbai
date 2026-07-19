"""The 200 m analysis grid and its permanent `cell_id`.

Every downstream table joins on `cell_id`, so this module produces the one artifact in the
pipeline that must never change meaning. `docs/conventions.md` forbids reindexing it.

Run standalone with:

    uv run python -m data_pipeline.grid
"""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import shapely

from data_pipeline.boundary import AREA_CRS, STORAGE_CRS
from data_pipeline.config import get_settings

CELL_SIZE_M = 200  # ADR-0007

# cell_id is derived from the cell's position on the UTM 43N grid, not from its position in
# whatever row order this script happens to produce.
#
# A sequential 0..N id looks simpler and is a trap: nudge the boundary, drop one coastal
# cell, and every id after it shifts by one. Saved scenarios and stored predictions would
# then silently point at the wrong ground. Anchoring to the projected coordinate system
# means a cell's id depends only on where it is on Earth — re-running against a different
# boundary adds and removes cells but never renumbers the ones that remain.
#
# cell_id = grid_row * ROW_STRIDE + grid_col
ROW_STRIDE = 1_000_000
MAX_COL = ROW_STRIDE - 1

# Cells are kept if they touch land at all; `land_fraction` records how much. Slivers along
# the coast are retained rather than filtered here so Phase 2 can decide on evidence how
# much land a cell needs before its LST average is trustworthy. Filtering now would bake a
# guess into the permanent cell set.
REPORT_THRESHOLDS = (0.10, 0.25, 0.50, 0.90)


def _snap_down(value: float, size: int) -> int:
    """Largest multiple of `size` at or below `value`."""
    return int(np.floor(value / size) * size)


def build_cells(study_area: gpd.GeoSeries) -> gpd.GeoDataFrame:
    """Tile the study area's bounding box with `CELL_SIZE_M` squares, anchored to UTM.

    The grid origin is the projected CRS origin itself, so the tiling is a property of
    EPSG:32643 and the cell size — never of the input geometry's extent.
    """
    minx, miny, maxx, maxy = study_area.total_bounds

    x0 = _snap_down(minx, CELL_SIZE_M)
    y0 = _snap_down(miny, CELL_SIZE_M)
    xs = np.arange(x0, maxx + CELL_SIZE_M, CELL_SIZE_M)
    ys = np.arange(y0, maxy + CELL_SIZE_M, CELL_SIZE_M)

    grid_x, grid_y = np.meshgrid(xs, ys)
    grid_x = grid_x.ravel()
    grid_y = grid_y.ravel()

    cols = (grid_x // CELL_SIZE_M).astype(np.int64)
    rows = (grid_y // CELL_SIZE_M).astype(np.int64)
    if cols.max() > MAX_COL or cols.min() < 0:
        raise ValueError(f"grid column index out of range for ROW_STRIDE={ROW_STRIDE}")

    geometry = shapely.box(grid_x, grid_y, grid_x + CELL_SIZE_M, grid_y + CELL_SIZE_M)

    return gpd.GeoDataFrame(
        {
            "cell_id": rows * ROW_STRIDE + cols,
            "grid_row": rows,
            "grid_col": cols,
        },
        geometry=geometry,
        crs=AREA_CRS,
    )


def build(*, write: bool = True) -> gpd.GeoDataFrame:
    """Produce the analysis grid: one row per cell, tagged with ward and land fraction."""
    settings = get_settings()
    wards = gpd.read_file(settings.processed_dir / "wards.geojson").to_crs(AREA_CRS)
    study_area = wards.geometry

    candidates = build_cells(study_area)
    print(f"[grid] {len(candidates):,} candidate cells over the bounding box")

    # Overlay against the wards rather than the dissolved union: it yields the land area
    # *and* the per-ward split in a single pass, so land_fraction and ward_code can never
    # disagree about which geometry they were derived from.
    pieces = gpd.overlay(candidates, wards[["ward_code", "geometry"]], how="intersection")
    pieces["piece_area"] = pieces.geometry.area
    print(f"[grid] {len(pieces):,} cell-by-ward intersection pieces")

    cell_area = float(CELL_SIZE_M**2)
    land = pieces.groupby("cell_id", as_index=False)["piece_area"].sum()
    land["land_fraction"] = (land["piece_area"] / cell_area).clip(upper=1.0)

    # A cell straddling a ward border belongs to whichever ward covers most of it. Without
    # this, ward aggregates would either double-count the cell or drop it.
    dominant = pieces.loc[pieces.groupby("cell_id")["piece_area"].idxmax()]
    dominant = dominant[["cell_id", "ward_code"]]

    grid = (
        candidates.merge(land[["cell_id", "land_fraction"]], on="cell_id", how="inner")
        .merge(dominant, on="cell_id", how="left")
        .sort_values("cell_id")
        .reset_index(drop=True)
    )

    # Centroids in the projected CRS, then converted — computing them in degrees would
    # place them slightly wrong, since a degree is not a constant distance.
    centroids = grid.geometry.centroid.to_crs(STORAGE_CRS)
    grid["centroid_lon"] = centroids.x.round(6)
    grid["centroid_lat"] = centroids.y.round(6)

    grid = grid.to_crs(STORAGE_CRS)
    _report(grid, wards)

    if write:
        dest = settings.interim_dir / "grid.parquet"
        grid.to_parquet(dest, index=False)
        print(f"[grid] wrote {dest}")

    return grid


def _report(grid: gpd.GeoDataFrame, wards: gpd.GeoDataFrame) -> None:
    """Print the checks that would catch a silently wrong grid."""
    if grid["cell_id"].duplicated().any():
        raise ValueError("duplicate cell_id — the grid is not a function of position")
    if grid["ward_code"].isna().any():
        raise ValueError(f"{int(grid['ward_code'].isna().sum())} cells have no ward")

    missing = set(wards["ward_code"]) - set(grid["ward_code"])
    if missing:
        raise ValueError(f"wards with no cells at all: {sorted(missing)}")

    covered = float(grid["land_fraction"].sum() * CELL_SIZE_M**2 / 1e6)
    ward_area = float(wards.geometry.area.sum() / 1e6)

    print(f"[grid] {len(grid):,} cells covering {covered:,.1f} km²")
    print(f"[grid]   ward area {ward_area:,.1f} km²  (difference {covered - ward_area:+.2f})")
    print(f"[grid]   cell_id range {grid['cell_id'].min():,} … {grid['cell_id'].max():,}")
    print("[grid]   land_fraction distribution:")
    for threshold in REPORT_THRESHOLDS:
        n = int((grid["land_fraction"] < threshold).sum())
        print(f"[grid]     < {threshold:.2f}  {n:>6,}  ({n / len(grid):>5.1%})")
    whole = int((grid["land_fraction"] >= 0.999).sum())
    print(f"[grid]     = 1.00  {whole:>6,}  ({whole / len(grid):>5.1%})  fully inland")

    per_ward = grid.groupby("ward_code").size().sort_values(ascending=False)
    print(
        f"[grid]   cells per ward: {per_ward.max()} max ({per_ward.idxmax()}), "
        f"{per_ward.min()} min ({per_ward.idxmin()})"
    )


if __name__ == "__main__":
    build()
