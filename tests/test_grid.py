"""The grid's `cell_id` is the pipeline's permanent join key. These lock its two guarantees:
it is a pure function of grid position, and it is stable when the study area changes."""

import geopandas as gpd
from shapely.geometry import box

from data_pipeline.grid import ROW_STRIDE, build_cells


def _series(minx, miny, maxx, maxy) -> gpd.GeoSeries:
    """A one-geometry GeoSeries in the grid's projected CRS (EPSG:32643)."""
    return gpd.GeoSeries([box(minx, miny, maxx, maxy)], crs=32643)


def test_cell_id_is_the_position_formula():
    cells = build_cells(_series(0, 0, 1000, 1000))
    assert (cells["cell_id"] == cells["grid_row"] * ROW_STRIDE + cells["grid_col"]).all()


def test_cell_ids_are_unique():
    cells = build_cells(_series(0, 0, 2000, 3000))
    assert cells["cell_id"].is_unique


def test_cell_id_is_position_stable():
    """A sub-region's cells must keep the exact ids they have in the larger tiling —
    the property that stops a boundary change from silently repointing saved scenarios."""
    big = build_cells(_series(0, 0, 4000, 4000))
    sub = build_cells(_series(1000, 1000, 3000, 3000))

    merged = sub.merge(big, on="cell_id", suffixes=("_sub", "_big"))
    assert len(merged) == len(sub)  # every sub cell exists in big under the same id
    assert (merged["grid_row_sub"] == merged["grid_row_big"]).all()
    assert (merged["grid_col_sub"] == merged["grid_col_big"]).all()
