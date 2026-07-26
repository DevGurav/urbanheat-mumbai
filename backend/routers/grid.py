"""GET /city/grid — the choropleth layer, the dashboard's main payload (api-reference.md).

Geometry simplification + gzip (already at app level) keep the ~12k-polygon response inside
Render's free-tier bandwidth (ADR-0003). The grid only changes when the pipeline re-runs, so
the response is safe to cache hard on the client side — no per-request recomputation here
beyond a simplify + optional bbox clip.
"""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Query, Request

from backend.errors import api_error

router = APIRouter(tags=["data"])

# layer name -> source column. `hvi` lives in its own frame (hvi.parquet) and only covers
# land cells (dataset.py TRAIN_MIN_LAND) — the inner merge below drops the rest for that layer.
LAYERS = {
    "lst": "lst_mean",
    "ndvi": "ndvi_mean",
    "built": "built_fraction",
    "hvi": "hvi",
}


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    parts = bbox.split(",")
    if len(parts) != 4:
        raise api_error(400, "invalid_bbox", "bbox must be 'minx,miny,maxx,maxy'")
    try:
        minx, miny, maxx, maxy = (float(p) for p in parts)
    except ValueError as exc:
        raise api_error(400, "invalid_bbox", "bbox values must be numeric") from exc
    if minx >= maxx or miny >= maxy:
        raise api_error(400, "invalid_bbox", "bbox must satisfy minx < maxx and miny < maxy")
    return minx, miny, maxx, maxy


@router.get("/city/grid")
def city_grid(
    request: Request,
    layer: Literal["lst", "ndvi", "hvi", "built"] = "lst",
    simplify: float = Query(0.0001, ge=0.0, le=0.01, description="Geometry tolerance, degrees"),
    bbox: str | None = Query(None, description="minx,miny,maxx,maxy — optional viewport filter"),
) -> dict:
    store = request.app.state.store
    col = LAYERS[layer]

    if layer == "hvi":
        frame = store.features[["cell_id", "ward_code", "geometry"]].merge(
            store.hvi[["cell_id", "hvi"]], on="cell_id", how="inner"
        )
    else:
        frame = store.features[["cell_id", "ward_code", "geometry", col]].copy()
    frame = frame.rename(columns={col: "value"})

    if bbox:
        minx, miny, maxx, maxy = _parse_bbox(bbox)
        frame = frame.cx[minx:maxx, miny:maxy]

    if simplify > 0:
        frame["geometry"] = frame.geometry.simplify(simplify, preserve_topology=True)
    frame["value"] = frame["value"].round(3)

    return json.loads(frame.to_json())
