"""GET /predict — the model's own LST prediction for a cell, vs. what Landsat observed
(api-reference.md). A transparency endpoint: how far is the fitted surface from the data?
Restricted to the model's training domain (land_fraction >= TRAIN_MIN_LAND) — the same
threshold `/explain` uses, since the model was never trained on mostly-sea cells.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.errors import api_error
from backend.schemas import PredictResponse
from data_pipeline.ml.dataset import TRAIN_MIN_LAND

router = APIRouter(tags=["model"])


@router.get("/predict", response_model=PredictResponse)
def predict(request: Request, cell_id: int) -> PredictResponse:
    store = request.app.state.store
    features = store.features

    match = features.loc[features["cell_id"] == cell_id]
    if match.empty:
        raise api_error(404, "cell_not_found", f"no cell with cell_id={cell_id}")
    cell = match.iloc[0]

    if cell["land_fraction"] < TRAIN_MIN_LAND:
        raise api_error(
            404,
            "cell_not_predictable",
            f"cell_id={cell_id} is below the land-fraction training threshold "
            f"({TRAIN_MIN_LAND}) — outside the model's domain, likely mostly sea",
        )

    feature_names = store.model_meta["feature_names"]
    X = features.loc[match.index, feature_names]
    predicted = float(store.model.predict(X)[0])
    observed = float(cell["lst_mean"])

    return PredictResponse(
        cell_id=cell_id,
        ward_code=str(cell["ward_code"]),
        predicted_lst=round(predicted, 2),
        observed_lst=round(observed, 2),
        residual=round(observed - predicted, 2),
        model_version=store.model_version,
    )
