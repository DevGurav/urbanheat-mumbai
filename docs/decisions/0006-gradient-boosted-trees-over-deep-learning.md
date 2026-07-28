# ADR-0006 — Gradient-boosted trees over deep learning

**Status:** Accepted
**Date:** 2026-07-17
**Phase:** 0

## Context

The learning task: predict LST per ~200 m cell from ~15–25 tabular predictors (NDVI, NDBI,
NDWI, albedo, land-cover fractions, building density, road density, population, elevation,
distance to coast, weather covariates). Dataset ≈ 20,000 rows × ~20 columns — small.

Two properties of this project constrain the model choice more than accuracy does:

1. **Explainability is the product, not a nicety.** The system's purpose is to tell a
   planner *why* a ward is hot and *what would change if they intervened*. A model that
   predicts well but cannot attribute is useless here.
2. **No GPU**, and the author must be able to defend every choice under review.

## Options considered

### A — CNN / U-Net on raster patches

**Pros** Captures spatial context and texture directly; state of the art for imagery;
impressive-sounding.
**Cons** Needs a GPU we do not have; ~20k samples is far too few for a CNN that would not
memorise; the entire raster-download problem that ADR-0001 deliberately eliminated comes
straight back (patches must be local); explainability drops to saliency maps, which are
qualitative — no per-feature ΔLST attribution, so the scenario engine loses its
foundation; weeks of training-loop debugging that buy nothing the report needs.

### B — Gradient-boosted trees (XGBoost / LightGBM)

**Pros** State of the art *for tabular data at this size* — this is the regime where GBTs
still beat neural nets; trains in seconds on a CPU, so feature iteration is a tight loop;
SHAP has an exact, fast tree explainer giving both global importance and per-cell
attribution — exactly the two outputs the product needs; handles mixed scales and
non-linear interactions without preprocessing ceremony; the dominant choice in the
published UHI-modelling literature, so results are comparable and the method is citable.
**Cons** No spatial context unless engineered in (neighbourhood aggregates must be explicit
features); can extrapolate poorly outside the training envelope — relevant, because the
scenario engine deliberately pushes features to unseen values; needs spatial
cross-validation or it will report a fantasy R².

### C — Linear / ridge regression

**Pros** Maximally interpretable; coefficients are the explanation; trivial to defend.
**Cons** UHI drivers interact non-linearly (vegetation's cooling saturates; coastal
proximity interacts with wind) — a linear model underfits badly. Still valuable as a
**baseline**, which is how it gets used.

### D — Random forest

**Pros** Robust, few knobs, SHAP-compatible.
**Cons** Generally edged out by boosting on this kind of tabular problem; larger artifacts.
Kept as a sanity-check comparator.

## Decision

**Gradient-boosted trees — XGBoost and LightGBM compared head-to-head, with ridge
regression as a baseline and random forest as a comparator.**

The deciding factor is that SHAP's tree explainer makes the model's attribution *exact and
per-cell*, which is what the entire recommendation and digital-twin layer stands on. A CNN
would trade that for saliency heatmaps and demand hardware we do not have, on a dataset far
too small to justify it. At 20k×20, boosting is not a compromise — it is the correct tool,
and the honest framing is that deep learning would be the *wrong* answer here rather than
an unaffordable luxury.

Reporting a baseline-to-boosting progression also makes the results section meaningful:
"R² 0.82" alone says nothing; "ridge 0.61 → LightGBM 0.82" shows what the non-linearity
bought.

## Consequences

**Positive**
- Trains in seconds on CPU → feature engineering iterates in a tight loop.
- SHAP gives global importance *and* per-cell attribution — the explainability the product
  requires, not a proxy for it.
- Scenario engine falls out naturally: perturb features → re-predict → ΔLST.
- Methodology matches the published UHI literature → defensible and comparable.
- Small artifacts (a few MB) deploy fine on Render's free tier.

**Negative**
- **Spatial autocorrelation will inflate random-split scores.** Neighbouring cells are near
  duplicates, so a random split leaks. Spatial block cross-validation is mandatory, and the
  gap between naive and blocked CV must be *reported*, not buried — it is one of the more
  interesting findings the report can carry.
- Spatial context requires explicit feature engineering (neighbourhood means, distance
  decays) rather than being learned.
- **Extrapolation risk in the scenario engine.** Pushing NDVI to values unseen in training
  produces confident nonsense. Scenario inputs must be clamped to the observed feature
  envelope, and this constraint is documented in `ml-methodology.md` and enforced in the
  engine.
- Tree models predict a plateau outside training range — ΔLST for extreme interventions
  will be under-stated. Stated as a limitation.

**Revisit if** the grid grows to multi-city at finer resolution *and* spatial context is
demonstrably the bottleneck — then a CNN on rasters becomes worth its cost. Not before.
