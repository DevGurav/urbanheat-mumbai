"""SHAP explanation of the saved model, with the physics gate (ml-methodology.md §4).

Global feature importance and per-cell attribution from a TreeExplainer, plus the gate that
checks the *sign* of each strong-prior driver against physics: vegetation and water must cool,
built-up must warm. A violation there (e.g. "vegetation warms") is a stop-and-fix — the model
or a feature is wrong. `albedo` is the known exception: its LST correlation is confounded to
the wrong sign (ADR-0008), so a **positive** albedo effect is *expected*, not a failure.

Run with:

    uv run python -m data_pipeline.ml.explain
"""

from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd
import shap

from data_pipeline.config import get_settings
from data_pipeline.ml.dataset import TRAIN_MIN_LAND, load_features

# Physical prior on the sign of each driver's effect on LST.
PHYSICS_PRIOR = {
    "ndbi_mean": "warm",
    "built_fraction": "warm",
    "built_neigh_mean": "warm",
    "impervious_fraction": "warm",
    "building_density": "warm",
    "road_density": "warm",
    "pop_density": "warm",
    "ndvi_mean": "cool",
    "ndvi_neigh_mean": "cool",
    "ndvi_p10": "cool",
    "tree_fraction": "cool",
    "water_fraction": "cool",
    "mangrove_fraction": "cool",
    "elevation_mean": "cool",
}
# The load-bearing subset the gate ENFORCES — a wrong sign on one of these means the model or
# a feature is genuinely broken. The rest of PHYSICS_PRIOR are collinear or low-importance
# features whose SHAP sign is credit-shared with a stronger same-direction driver and therefore
# unreliable (data-dictionary: built/NDBI/impervious are near-collinear). Those are reported,
# not gated — gating them produces false alarms, not physics failures.
GATED = frozenset(
    {
        "ndbi_mean",
        "built_fraction",
        "built_neigh_mean",
        "pop_density",
        "ndvi_mean",
        "ndvi_neigh_mean",
        "tree_fraction",
        "water_fraction",
    }
)
# Physics says reflective → cool; the observed/model sign is warm because dark water is cool
# and bright bare ground is hot. Expected, reported, never gated (ADR-0008).
CONFOUNDED = {"albedo": "cool"}


def _direction(feature_vals: np.ndarray, shap_vals: np.ndarray) -> str:
    """'warm' if raising the feature raises the prediction, else 'cool' ('flat' if undefined)."""
    if np.std(feature_vals) < 1e-12 or np.std(shap_vals) < 1e-12:
        return "flat"
    return "warm" if np.corrcoef(feature_vals, shap_vals)[0, 1] > 0 else "cool"


def physics_violations(directions: dict[str, str]) -> list[str]:
    """Load-bearing drivers whose SHAP sign contradicts physics. Empty = gate passes."""
    return [
        f"{f}: expected {PHYSICS_PRIOR[f]}, got {directions.get(f)}"
        for f in GATED
        if directions.get(f) != PHYSICS_PRIOR[f]
    ]


def explain(*, save: bool = True) -> pd.DataFrame:
    """Compute SHAP global importance + per-cell attribution and run the physics gate."""
    settings = get_settings()
    model = joblib.load(settings.model_dir / "model.joblib")
    meta = json.loads((settings.model_dir / "model_meta.json").read_text())
    feature_names: list[str] = meta["feature_names"]

    frame = load_features()
    land = frame[frame["land_fraction"] >= TRAIN_MIN_LAND].reset_index(drop=True)
    X = land[feature_names]
    print(f"[explain] SHAP over {len(X):,} cells × {len(feature_names)} features ({meta['model']})")

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    mean_abs = np.abs(shap_values).mean(axis=0)
    directions = {
        f: _direction(X[f].to_numpy(), shap_values[:, i]) for i, f in enumerate(feature_names)
    }
    importance = (
        pd.DataFrame({"feature": feature_names, "mean_abs_shap": mean_abs})
        .assign(direction=lambda d: d["feature"].map(directions))
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )

    _report(importance, directions)

    if save:
        _save(settings, importance, land["cell_id"], shap_values, feature_names)
    return importance


def _report(importance: pd.DataFrame, directions: dict[str, str]) -> None:
    print("\n[explain] top drivers by mean |SHAP| (°C):")
    for _, r in importance.head(12).iterrows():
        print(f"[explain]   {r['feature']:20} {r['mean_abs_shap']:5.2f}  ({r['direction']})")

    # The physics gate — enforced on the load-bearing drivers only.
    print("\n[explain] physics gate (load-bearing drivers):")
    for f in sorted(GATED, key=lambda f: -importance.set_index("feature").loc[f, "mean_abs_shap"]):
        got, want = directions.get(f), PHYSICS_PRIOR[f]
        print(f"[explain]   {f:18} {got:4} vs {want:4} prior   {'OK' if got == want else 'FLIP'}")

    violations = physics_violations(directions)
    if violations:
        raise ValueError(
            "PHYSICS GATE FAILED — a load-bearing driver has the wrong sign:\n  "
            + "\n  ".join(violations)
        )
    print("[explain] gate PASSED — every load-bearing driver matches physics.")

    for feat, physics in CONFOUNDED.items():
        got = directions.get(feat)
        if got and got != physics:
            note = f"{feat}='{got}' — expected (ADR-0008), physics says {physics}"
            print(f"[explain] confound: {note}")

    # Collinear/low-importance features whose sign is credit-shared, not a physics failure.
    shared = [
        f
        for f, want in PHYSICS_PRIOR.items()
        if f not in GATED and directions.get(f) not in (want, "flat", None)
    ]
    if shared:
        print("[explain] credit-sharing (collinear, sign not gated):")
        for f in shared:
            print(
                f"[explain]   {f:18} '{directions[f]}' (prior {PHYSICS_PRIOR[f]}) — shares credit"
            )


def _save(settings, importance, cell_ids, shap_values, feature_names) -> None:
    importance.to_json(settings.model_dir / "shap_global.json", orient="records", indent=2)
    per_cell = pd.DataFrame(shap_values, columns=[f"shap_{f}" for f in feature_names])
    per_cell.insert(0, "cell_id", cell_ids.to_numpy())
    per_cell.to_parquet(settings.model_dir / "shap_values.parquet", index=False)
    print(f"[explain] saved shap_global.json + shap_values.parquet to {settings.model_dir}")


if __name__ == "__main__":
    explain()
