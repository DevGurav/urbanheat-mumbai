"""Scenario engine / digital twin (ml-methodology.md §6).

`simulate` perturbs a cell's features and re-predicts LST, clamped to the training envelope so
it can never extrapolate into confident nonsense (ADR-0006). Two levers, two mechanisms:

- **Greening** (raise NDVI) goes *through the model* — its NDVI cooling is SHAP-validated and
  corroborated by literature (~1.39 °C per unit NDVI in Indian metros, Grover & Singh 2015).
- **Cool roofs** (raise albedo) do NOT go through the model — the model's albedo term is the
  confound (ADR-0008). ΔLST comes from a *cited* coefficient (Li et al. 2014).

Every output is **correlational, not causal**: "cells like this but greener are ~X °C cooler",
not "this will cool by X °C". A relative planning aid, not a guarantee.

Run with:

    uv run python -m data_pipeline.ml.scenario
"""

from __future__ import annotations

import json

import joblib
import pandas as pd

from data_pipeline.config import get_settings
from data_pipeline.ml.dataset import TRAIN_MIN_LAND, load_features

# Cited cool-roof coefficient (Li, Bou-Zeid & Oppenheimer 2014, Environ. Res. Lett. 9 055002):
# 50 % cool-roof coverage → ~1.7 °C surface-UHI reduction. A cell's treatable area is its built
# fraction, so ΔLST = −(1.7 / 0.5) · built_fraction · coverage. Literature-derived estimate, not
# a Mumbai measurement — reported as such. Used directly; the model's albedo term is confounded.
COOL_ROOF_C_PER_BUILT = 1.7 / 0.5  # ≈ 3.4 °C per unit (built_fraction × coverage)
GREENING_NDVI_TARGET = 0.4  # a moderately-green cell; raise cells below this toward it


def training_envelope(
    land: pd.DataFrame, feature_names: list[str]
) -> dict[str, tuple[float, float]]:
    """Per-feature [min, max] over the training cells — the box scenarios may not leave."""
    return {f: (float(land[f].min()), float(land[f].max())) for f in feature_names}


def _clamp(X: pd.DataFrame, envelope: dict[str, tuple[float, float]]) -> pd.DataFrame:
    for feat, (lo, hi) in envelope.items():
        X[feat] = X[feat].clip(lo, hi)
    return X


def greening_delta(
    land: pd.DataFrame,
    model,
    feature_names: list[str],
    envelope,
    *,
    ndvi_target: float = GREENING_NDVI_TARGET,
) -> pd.Series:
    """ΔLST from raising each cell's NDVI toward `ndvi_target` — through the model, clamped."""
    X = land[feature_names].copy()
    new = X.copy()
    rise = (ndvi_target - new["ndvi_mean"]).clip(lower=0)
    new["ndvi_mean"] = new["ndvi_mean"] + rise
    if "ndvi_neigh_mean" in new:  # the neighbourhood greens partially too
        new["ndvi_neigh_mean"] = new["ndvi_neigh_mean"] + 0.5 * rise
    new = _clamp(new, envelope)
    return pd.Series(model.predict(new) - model.predict(X), index=land.index)


def cool_roof_delta(land: pd.DataFrame, *, coverage: float = 1.0) -> pd.Series:
    """ΔLST from cool roofs — a cited coefficient scaled by built fraction, NOT the model."""
    return -COOL_ROOF_C_PER_BUILT * land["built_fraction"] * coverage


def _load_model():
    settings = get_settings()
    model = joblib.load(settings.model_dir / "model.joblib")
    meta = json.loads((settings.model_dir / "model_meta.json").read_text())
    return model, meta["feature_names"]


def build(*, write: bool = True) -> pd.DataFrame:
    """Run the demonstration greening scenario and report a sensible ΔLST map."""
    settings = get_settings()
    model, feature_names = _load_model()
    frame = load_features()
    land = frame[frame["land_fraction"] >= TRAIN_MIN_LAND].reset_index(drop=True)
    envelope = training_envelope(land, feature_names)

    green_raw = greening_delta(land, model, feature_names, envelope)
    # Greening cannot warm a cell all-else-equal (shade + evapotranspiration). The correlational
    # tree model occasionally predicts small spurious warming where raising NDVI pushes a cell
    # off the training manifold (high built fraction + high NDVI, rare in the data), so the
    # delivered map is floored at 0 — the physically-correct bound. The count is reported. A
    # monotone-constrained model (v2) would remove the need for the floor.
    green_map = green_raw.clip(upper=0.0)
    cool = cool_roof_delta(land)

    out = land[["cell_id", "ward_code", "lst_mean", "ndvi_mean", "built_fraction"]].copy()
    out["dlst_greening"] = green_map.to_numpy()
    out["dlst_cool_roof"] = cool.to_numpy()

    _report(out, green_raw)

    if write:
        dest = settings.processed_dir / "scenario_greening.parquet"
        out.to_parquet(dest, index=False)
        print(f"\n[scenario] wrote {dest} ({len(out):,} cells)")
    return out


def _report(out: pd.DataFrame, green_raw: pd.Series) -> None:
    changed = out["ndvi_mean"] < GREENING_NDVI_TARGET  # cells the scenario actually greens
    greened = out[changed]
    print(
        f"[scenario] greening to NDVI {GREENING_NDVI_TARGET}: {changed.sum():,} of {len(out):,} "
        f"cells are below target and change"
    )
    mean_c, best_c = greened["dlst_greening"].mean(), greened["dlst_greening"].min()
    print(f"[scenario]   greened ΔLST: mean {mean_c:+.2f} °C, best {best_c:+.2f} °C (floored at 0)")
    # Transparency on the floor: how often the raw model predicted spurious warming.
    floored = int((green_raw[changed] > 0.05).sum())
    print(
        f"[scenario]   floored to 0: {floored:,} changed cells the raw model warmed (off-manifold)"
    )

    ward = greened.groupby("ward_code")["dlst_greening"].mean().sort_values()
    print("[scenario]   wards with the most greening cooling (mean ΔLST):")
    for w, d in ward.head(5).items():
        print(f"[scenario]     {w:5} {d:+.2f} °C")

    cool = out["dlst_cool_roof"]
    print(
        f"[scenario] cool-roof (cited coeff, Li et al. 2014): mean {cool.mean():+.2f} °C, "
        f"best {cool.min():+.2f} °C over built cells"
    )
    print("[scenario] NOTE: correlational, not causal — 'cells like this but greener are cooler'.")


if __name__ == "__main__":
    build()
