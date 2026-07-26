"""Heat Vulnerability Index and ward hotspot ranking (ml-methodology.md §5).

HVI = w_heat·norm(lst_mean) + w_exp·norm(pop_density) + w_green·norm(1 − ndvi_mean), min–max
normalised over land cells. It is a **relative prioritisation tool, not a health-risk score**
(ADR-0005) — built on mid-morning surface temperature, with no health, age or income data.

The weights are a judgement call, so the mandatory check is **sensitivity**: does the top-10
ward ranking survive reasonable weight perturbations? If it flips under small changes the index
is too fragile to publish. HVI is derived from `lst_mean` (the model's target), so it is written
to its own `hvi.parquet` and never enters the model's feature table.

Run with:

    uv run python -m data_pipeline.ml.hvi
"""

from __future__ import annotations

import pandas as pd

from data_pipeline.config import get_settings
from data_pipeline.ml.dataset import TRAIN_MIN_LAND, load_features

# Starting weights (ml-methodology §5): heat and exposure equal, lack-of-green a secondary
# amplifier that also flags where the cheapest lever (planting) applies. Exposed as a parameter
# so a planner can re-weight to their own policy.
WEIGHTS = {"heat": 0.4, "exposure": 0.4, "lack_green": 0.2}


def _minmax(s: pd.Series) -> pd.Series:
    return (s - s.min()) / (s.max() - s.min())


def compute_hvi(land: pd.DataFrame, weights: dict[str, float] = WEIGHTS) -> pd.DataFrame:
    """Per-cell HVI and its city-wide hotspot rank (1 = most vulnerable)."""
    heat = _minmax(land["lst_mean"])
    exposure = _minmax(land["pop_density"])
    lack_green = _minmax(1 - land["ndvi_mean"])

    hvi = (
        weights["heat"] * heat + weights["exposure"] * exposure + weights["lack_green"] * lack_green
    )
    out = land[["cell_id", "ward_code"]].copy()
    out["hvi_heat"] = heat.to_numpy()
    out["hvi_exposure"] = exposure.to_numpy()
    out["hvi_lack_green"] = lack_green.to_numpy()
    out["hvi"] = hvi.to_numpy()
    out["hotspot_rank"] = hvi.rank(ascending=False, method="min").astype(int).to_numpy()
    return out


def ward_ranking(hvi_df: pd.DataFrame) -> pd.Series:
    """Mean HVI per ward, highest first — the planner-facing hotspot list."""
    return hvi_df.groupby("ward_code")["hvi"].mean().sort_values(ascending=False)


# Weight variants spanning reasonable planner preferences, for the sensitivity check.
_VARIANTS = {
    "heat-heavy": {"heat": 0.5, "exposure": 0.3, "lack_green": 0.2},
    "exposure-heavy": {"heat": 0.3, "exposure": 0.5, "lack_green": 0.2},
    "equal": {"heat": 1 / 3, "exposure": 1 / 3, "lack_green": 1 / 3},
    "green-heavy": {"heat": 0.35, "exposure": 0.35, "lack_green": 0.30},
    "heat+exposure only": {"heat": 0.5, "exposure": 0.5, "lack_green": 0.0},
}


def sensitivity(land: pd.DataFrame, base: dict[str, float] = WEIGHTS) -> dict:
    """Does the ward ranking survive weight perturbations? Reports top-10 overlap + Spearman."""
    base_rank = ward_ranking(compute_hvi(land, base))
    base_top10 = set(base_rank.head(10).index)

    print("[hvi] sensitivity — ward ranking under weight perturbations (base 0.4/0.4/0.2):")
    results = {}
    for name, weights in _VARIANTS.items():
        rank = ward_ranking(compute_hvi(land, weights))
        overlap = len(base_top10 & set(rank.head(10).index))
        spearman = float(base_rank.corr(rank, method="spearman"))
        results[name] = {"top10_overlap": overlap, "spearman": spearman}
        print(f"[hvi]   {name:20} top-10 overlap {overlap}/10   Spearman ρ={spearman:.3f}")
    return results


def build(*, write: bool = True) -> pd.DataFrame:
    settings = get_settings()
    frame = load_features()
    land = frame[frame["land_fraction"] >= TRAIN_MIN_LAND].reset_index(drop=True)
    print(f"[hvi] {len(land):,} land cells, weights {WEIGHTS}")

    hvi_df = compute_hvi(land)
    wards = ward_ranking(hvi_df)
    print("\n[hvi] most heat-vulnerable wards (mean HVI):")
    for ward, score in wards.head(8).items():
        print(f"[hvi]   {ward:5} {score:.3f}")

    print()
    sensitivity(land)

    if write:
        dest = settings.processed_dir / "hvi.parquet"
        hvi_df.to_parquet(dest, index=False)
        print(f"\n[hvi] wrote {dest} ({len(hvi_df):,} cells)")
    return hvi_df


if __name__ == "__main__":
    build()
