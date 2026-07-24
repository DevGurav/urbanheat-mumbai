"""Shared Earth Engine reduction — reduce a composite over every grid cell, in chunks.

Factored out of the Landsat stage so every raster source (Sentinel-2, WorldPop, SRTM, …)
shares one code path for the cell reduction and the study-area extent.

`reduceRegions` runs server-side, but the reduced table still comes down through `getInfo`,
and one call over ~12k cells exceeds the payload limit. Cells are therefore sent up in
chunks, each returning a fully reduced table — the "export aggregates" pattern ADR-0001
requires, not the per-cell `getInfo` loop it forbids. The distinction is what each request
computes, not how many requests there are.
"""

from __future__ import annotations

import time

import ee
import geopandas as gpd
import pandas as pd

from data_pipeline.config import Settings

CHUNK_SIZE = 500
TILE_SCALE = 4  # splits a chunk into smaller tiles when it would exceed the memory limit


def study_region(settings: Settings) -> ee.Geometry:
    """Bounding rectangle of the full grid, for `filterBounds`.

    Always the full grid's extent — never a caller's cell subset. A smoke test that reduces
    200 cells must still filter the same image collection the full run does, or it is not
    testing the full run. `geodesic=False` because the grid is planar in EPSG:32643.
    """
    grid = gpd.read_parquet(settings.interim_dir / "grid.parquet")
    bounds = [float(b) for b in grid.total_bounds]
    return ee.Geometry.Rectangle(bounds, proj="EPSG:4326", geodesic=False)


def _cells_to_fc(chunk: gpd.GeoDataFrame) -> ee.FeatureCollection:
    """Convert a chunk of grid cells to an Earth Engine FeatureCollection.

    Cells go up as explicit polygons with `geodesic=False`: they were built as squares in
    EPSG:32643, so their edges are straight in projection. Letting Earth Engine assume
    geodesic edges would bow them slightly outward.
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


def reduce_to_cells(
    image: ee.Image,
    grid: gpd.GeoDataFrame,
    band_names: list[str],
    *,
    scale: float,
    label: str = "reduce",
    reducer: ee.Reducer | None = None,
    chunk_size: int = CHUNK_SIZE,
) -> pd.DataFrame:
    """Reduce `image` over every cell in `grid`, returning `cell_id` + one column per band.

    `band_names` are the bands of `image` to read back; with the default mean reducer,
    `reduceRegions` names each output property after its band. Callers rename as needed.
    """
    reducer = reducer if reducer is not None else ee.Reducer.mean()
    rows: list[dict] = []
    n_chunks = (len(grid) + chunk_size - 1) // chunk_size
    started = time.time()

    for i in range(n_chunks):
        chunk = grid.iloc[i * chunk_size : (i + 1) * chunk_size]
        reduced = image.reduceRegions(
            collection=_cells_to_fc(chunk),
            reducer=reducer,
            scale=scale,
            tileScale=TILE_SCALE,
        )

        for feature in reduced.getInfo()["features"]:
            props = feature["properties"]
            row: dict = {"cell_id": props["cell_id"]}
            for band in band_names:
                row[band] = props.get(band)
            rows.append(row)

        elapsed = time.time() - started
        done = i + 1
        eta = elapsed / done * (n_chunks - done)
        print(
            f"[{label}]   chunk {done}/{n_chunks}  {len(rows):,} cells  "
            f"{elapsed:,.0f}s elapsed, ~{eta:,.0f}s left",
            flush=True,
        )

    return pd.DataFrame(rows)
