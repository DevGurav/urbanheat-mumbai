"""The Phase 2 model ladder (ml-methodology.md §3).

mean floor → ridge → random forest → XGBoost → LightGBM. Every rung is scored under both
ward-grouped spatial CV (the honest number) and a naive random split (for the gap). The best
spatial-RMSE model is refit on the full training set and saved to `models/`.

Run with:

    uv run python -m data_pipeline.ml.train
"""

from __future__ import annotations

import json
import time

import joblib
from lightgbm import LGBMRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from data_pipeline.config import get_settings
from data_pipeline.ml.cv import random_cv, spatial_cv
from data_pipeline.ml.dataset import TARGET, TRAIN_MIN_LAND, build_dataset

RANDOM_STATE = 42


def model_ladder() -> dict[str, object]:
    """The models to compare. Trees use light, sensible defaults — no heavy tuning is
    warranted at ~11k rows × 30 features (ADR-0006). Ridge is scaled; trees are scale-free."""
    return {
        "mean_floor": DummyRegressor(strategy="mean"),
        "ridge": Pipeline([("scale", StandardScaler()), ("model", Ridge(alpha=1.0))]),
        "random_forest": RandomForestRegressor(
            n_estimators=300, n_jobs=-1, random_state=RANDOM_STATE
        ),
        "xgboost": XGBRegressor(
            n_estimators=400,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=-1,
            random_state=RANDOM_STATE,
        ),
        "lightgbm": LGBMRegressor(
            n_estimators=400,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            n_jobs=-1,
            random_state=RANDOM_STATE,
            verbose=-1,
        ),
    }


def run(*, save: bool = True) -> dict:
    data = build_dataset()
    print(f"[train] scoring {len(model_ladder())} models under spatial + random 5-fold CV\n")

    rows = []
    for name, model in model_ladder().items():
        start = time.time()
        sp = spatial_cv(model, data.X, data.y, data.groups)
        rnd = random_cv(model, data.X, data.y)
        elapsed = time.time() - start
        gap = rnd["r2"] - sp["r2"]
        rows.append({"model": name, "spatial": sp, "random": rnd, "fit_s": elapsed})
        print(
            f"[train] {name:14} spatial R²={sp['r2']:6.3f} RMSE={sp['rmse']:5.2f}  |  "
            f"random R²={rnd['r2']:6.3f}  ΔR²={gap:+.3f}  |  {elapsed:4.1f}s"
        )

    _print_table(rows)

    # Select on the honest metric: lowest spatial RMSE, excluding the floor.
    ranked = sorted(
        (r for r in rows if r["model"] != "mean_floor"), key=lambda r: r["spatial"]["rmse"]
    )
    best = ranked[0]
    print(
        f"\n[train] selected: {best['model']} (spatial RMSE {best['spatial']['rmse']:.2f} °C, "
        f"R² {best['spatial']['r2']:.3f})"
    )

    if save:
        _save(best["model"], data, rows)
    return {"rows": rows, "best": best["model"]}


def _print_table(rows: list[dict]) -> None:
    header = f"{'model':14} {'sp_R2':>7} {'sp_RMSE':>8} {'sp_MAE':>7} {'rand_R2':>8} {'ΔR2':>7}"
    print(f"\n[train] {header}")
    for r in rows:
        sp, rnd = r["spatial"], r["random"]
        print(
            f"[train] {r['model']:14} {sp['r2']:>7.3f} {sp['rmse']:>8.2f} {sp['mae']:>7.2f} "
            f"{rnd['r2']:>8.3f} {rnd['r2'] - sp['r2']:>+7.3f}"
        )


def _save(name: str, data, rows: list[dict]) -> None:
    """Refit the chosen model on the full training set and persist it with its metadata."""
    models_dir = get_settings().model_dir
    models_dir.mkdir(parents=True, exist_ok=True)

    model = model_ladder()[name]
    model.fit(data.X, data.y)
    joblib.dump(model, models_dir / "model.joblib")

    meta = {
        "model": name,
        "target": TARGET,
        "train_min_land": TRAIN_MIN_LAND,
        "n_train_cells": int(len(data.X)),
        "feature_names": data.feature_names,
        "cv": "GroupKFold(ward_code), 5 folds (ADR-0008)",
        "metrics": {r["model"]: {"spatial": r["spatial"], "random": r["random"]} for r in rows},
    }
    (models_dir / "model_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[train] saved model.joblib + model_meta.json to {models_dir}")


if __name__ == "__main__":
    run()
