"""GET /hotspots — ranked wards or cells by HVI or LST, each with its top SHAP driver
(api-reference.md). Pure aggregation over the in-memory store — no model call.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
from fastapi import APIRouter, Query, Request

from backend.schemas import HotspotEntry, HotspotsResponse

router = APIRouter(tags=["data"])


def _top_driver(shap_row: pd.Series, shap_cols: list[str]) -> tuple[str, float]:
    """The feature with the largest |SHAP| for one cell, and its signed value."""
    vals = shap_row[shap_cols]
    top_col = vals.abs().idxmax()
    return top_col.removeprefix("shap_"), float(vals[top_col])


@router.get("/hotspots", response_model=HotspotsResponse)
def hotspots(
    request: Request,
    n: int = Query(10, ge=1, le=100),
    by: Literal["hvi", "lst"] = "hvi",
    unit: Literal["ward", "cell"] = "ward",
) -> HotspotsResponse:
    store = request.app.state.store
    shap_cols = [c for c in store.shap.columns if c != "cell_id"]

    if by == "hvi":
        base = store.hvi[["cell_id", "ward_code", "hvi"]].merge(
            store.features[["cell_id", "population"]], on="cell_id", how="left"
        )
        value_col = "hvi"
    else:
        base = store.features[["cell_id", "ward_code", "lst_mean", "population"]].copy()
        value_col = "lst_mean"

    shap_by_cell = store.shap.set_index("cell_id")
    entries: list[HotspotEntry] = []

    if unit == "cell":
        top = base.sort_values(value_col, ascending=False).head(n)
        for _, row in top.iterrows():
            cell_id = int(row["cell_id"])
            driver, shap_c = None, None
            if cell_id in shap_by_cell.index:
                driver, shap_c = _top_driver(shap_by_cell.loc[cell_id], shap_cols)
            entries.append(
                HotspotEntry(
                    id=str(cell_id),
                    ward_code=str(row["ward_code"]),
                    value=round(float(row[value_col]), 3),
                    population=float(row["population"]),
                    top_driver=driver,
                    top_driver_shap_c=round(shap_c, 3) if shap_c is not None else None,
                )
            )
    else:
        agg = base.groupby("ward_code").agg(
            value=(value_col, "mean"), population=("population", "sum")
        )
        top_wards = agg.sort_values("value", ascending=False).head(n)

        # Mean |SHAP| per ward per feature — the ward's dominant driver, not a single cell's.
        shap_with_ward = store.shap.merge(
            store.features[["cell_id", "ward_code"]], on="cell_id", how="left"
        )
        ward_mean_abs = shap_with_ward.groupby("ward_code")[shap_cols].apply(
            lambda g: g.abs().mean()
        )

        for ward_code, row in top_wards.iterrows():
            driver = None
            if ward_code in ward_mean_abs.index:
                driver = ward_mean_abs.loc[ward_code].idxmax().removeprefix("shap_")
            entries.append(
                HotspotEntry(
                    id=str(ward_code),
                    ward_code=str(ward_code),
                    value=round(float(row["value"]), 3),
                    population=float(row["population"]),
                    top_driver=driver,
                    top_driver_shap_c=None,  # a ward mean, not one cell's signed SHAP
                )
            )

    return HotspotsResponse(
        by=by,
        unit=unit,
        model_version=store.model_version,
        data_version=store.data_version,
        results=entries,
    )
