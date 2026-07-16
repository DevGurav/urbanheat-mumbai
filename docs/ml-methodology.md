# ML Methodology

The modelling design, the validation strategy, and the honest limitations. This document
becomes the methodology chapter of the final report.

**Status:** design, written before implementation. Sections marked *[Phase 2]* get filled
with real numbers as the work lands. **No result is recorded here until it is measured.**

---

## 1. Problem statement

**Task** Supervised regression.
**Unit** One ~200 m grid cell of Greater Mumbai (≈15–20k cells).
**Target** `lst_mean` — dry-season median land surface temperature, °C (ADR-0005).
**Predictors** ~20 tabular features: vegetation, built-up, albedo, land cover, density,
terrain, coastal distance, population (see [data-dictionary.md](data-dictionary.md)).
**Model** Gradient-boosted trees (ADR-0006).

**Why regression and not classification.** "Hotspot" is a decision threshold applied to a
continuous field, not a natural category. Predicting °C keeps the threshold in the
planner's hands and — critically — makes the scenario engine meaningful: ΔLST in degrees is
actionable, "moved from class 3 to class 2" is not.

**What the model is actually for.** Accuracy is a means, not the end. The model exists to
(a) attribute each cell's heat to its causes via SHAP and (b) support counterfactual
simulation. A model with R² 0.75 and trustworthy attribution beats R² 0.95 that leaked.

---

## 2. Validation strategy — the central methodological issue

**The problem.** Adjacent grid cells are near-duplicates: similar NDVI, similar built-up,
similar temperature. Under a random train/test split, a cell's own neighbours sit in the
training set. The model can effectively look up the answer. Reported R² would be inflated,
possibly badly, and the model would still fail on any genuinely unseen neighbourhood.

This is spatial autocorrelation, and it is the single easiest way to produce an
impressive-looking and worthless result. It is also exactly what a viva panel probes.

**The fix — spatial block cross-validation.** Partition the city into contiguous spatial
blocks (candidate: BMC wards, ~24 units — administratively meaningful and roughly the scale
at which recommendations are made; fallback: a k-km grid of blocks if wards are too uneven).
Hold out **whole blocks**, so no held-out cell has a neighbour in training. This measures
what we actually claim: *given a neighbourhood the model has never seen, can it predict its
heat from its physical characteristics?*

**Both numbers get reported.** Naive random-split CV alongside blocked CV. The gap between
them is a finding, not an embarrassment — it quantifies how much of an apparently good
score is autocorrelation. Reporting only the blocked (lower, honest) number without the
contrast wastes the insight.

*[Phase 2]* Naive R²: ___ · Blocked R²: ___ · Gap: ___

---

## 3. Model progression

Each step must justify the added complexity. Report the whole ladder — a single number in
isolation says nothing.

| Step | Model | Purpose |
|---|---|---|
| 0 | **Mean predictor** | Floor. R² = 0 by construction |
| 1 | **Ridge regression** | Linear baseline — how much is captured by "less green + more concrete = hotter"? |
| 2 | **Random forest** | Non-linearity without boosting; robustness comparator |
| 3 | **XGBoost** | Primary candidate |
| 4 | **LightGBM** | Primary candidate — faster; compare head-to-head |

Selection: best blocked-CV RMSE, ties broken toward the simpler and more stable model.

*[Phase 2]* Results table: model · naive R² · blocked R² · RMSE · MAE · fit time

**Metrics** RMSE (°C — primary, same unit as the target, penalises the large errors that
matter), MAE (°C — typical error, robust), R² (variance explained — reported for
comparability with the literature, never alone).

**Hyperparameters** Modest random search over depth, learning rate, estimators, subsample,
regularisation — inside the blocked CV, not outside it. Tuning against the test fold is
leakage by another name. Given ~20k rows, defaults are likely close to optimal; this is not
where the project's time goes.

---

## 4. Explainability

**SHAP TreeExplainer** — exact for tree ensembles, fast, and the reason ADR-0006 chose
trees.

- **Global** — beeswarm + mean |SHAP| bar. Expected: NDVI and built fraction dominate,
  `dist_coast` strong for Mumbai specifically. *[Phase 2]* Confirm or explain surprises.
- **Local** — per-cell waterfall: "this cell is 4.2 °C above the city mean; +2.1 from low
  NDVI, +1.4 from high built fraction, −0.3 from coastal proximity." **This is the
  product** — it powers `/explain/{cell_id}` and the Copilot's answers.
- **Dependence plots** — e.g. NDVI vs SHAP reveals whether cooling saturates. Physically
  expected, and worth showing if the model recovers it, because it means the model learned
  physics rather than noise.

**Sanity gate.** If SHAP directions contradict physics — vegetation *increasing* predicted
heat — the model is wrong regardless of R². Investigate before proceeding. Record any such
episode in `devlog.md`; it is exactly the kind of thing that makes a good report.

---

## 5. Heat Vulnerability Index

Prioritisation needs more than temperature — the hottest cell may be an empty industrial
roof, while a slightly cooler dense settlement holds thousands of people.

```
HVI = w₁ · norm(lst_mean) + w₂ · norm(pop_density) + w₃ · norm(1 − ndvi_mean)
```

Min–max normalised city-wide. Starting weights **0.4 / 0.4 / 0.2** — heat and exposure
weighted equally, lack-of-green as a secondary amplifier that also flags where the cheapest
lever (planting) applies.

**These weights are a judgement call, not a derived truth.** Requirements:
- Justify against published HVI literature (`references.md`) — many use census deprivation
  indicators unavailable at this resolution for Mumbai.
- **Sensitivity analysis is mandatory** *[Phase 2]*: does the top-10 ward ranking survive
  reasonable weight perturbations? If ranking flips under small changes, the index is too
  fragile to publish and needs rethinking.
- Expose weights as API parameters so a planner can re-weight to their own policy.

**HVI is a relative prioritisation tool, not a health-risk score** (ADR-0005). It is built
on mid-morning surface temperature and contains no health, age or income data.

---

## 6. Scenario engine (digital twin)

```
simulate(cell_ids, deltas) → ΔLST
  1. Load the cells' current feature vectors
  2. Apply the intervention's feature deltas
  3. Clamp every value to the observed training envelope   ← non-negotiable
  4. Re-predict LST
  5. ΔLST = LST_new − LST_current
```

**Intervention → feature mapping** *[Phase 2 — coefficients from literature, each cited]*

| Intervention | Feature changes | Source |
|---|---|---|
| Urban forestry / tree planting | `ndvi_mean` ↑, `tree_fraction` ↑, `albedo` slight ↑ | *cite* |
| Cool/reflective roofs | `albedo` ↑ (~0.2→0.6 on treated area) | *cite* |
| Green roofs | `ndvi_mean` ↑, `built_fraction` unchanged | *cite* |
| Water body / restoration | `ndwi_mean` ↑, `dist_water` ↓ | *cite* |
| Depaving / permeable surfaces | `impervious_fraction` ↓, `ndvi_mean` ↑ | *cite* |

**Limitations that must ship with every scenario output — stating these is the difference
between a defensible tool and a fabrication:**

1. **Correlational, not causal.** The model learned associations across space, not the
   physics of intervention. "Cells like this, but greener, are ~2 °C cooler" — *not* "this
   will cool by 2 °C." Every output must be phrased in the former register.
2. **Extrapolation is clamped.** Pushing NDVI beyond the training envelope produces
   confident nonsense (ADR-0006). Clamping is enforced in code; scenarios that hit the clamp
   must say so in their response rather than silently returning a capped number.
3. **No feedback effects.** Real greening changes humidity, wind and neighbouring cells.
   The model treats cells independently.
4. **Cost figures are literature-derived ranges**, not Mumbai procurement quotes. Order of
   magnitude, and labelled as such.

A physics-based check against published cooling ranges (e.g. urban trees ≈ 1–3 °C surface
cooling) is a useful plausibility gate. If the model claims 15 °C, something is broken.

---

## 7. Known limitations *(report-ready — write these up honestly)*

| # | Limitation | Impact |
|---|---|---|
| 1 | Surface ≠ air temperature | Outputs are not what people feel; labelled *surface* throughout |
| 2 | ~10:30 overpass only | Misses the 3 pm peak and the health-critical night-time UHI |
| 3 | Dry season only | No monsoon or winter picture (ADR-0005) |
| 4 | Correlational model | Scenarios are analogies, not causal predictions |
| 5 | 200 m cells, 100 m native thermal | No street-level claims |
| 6 | Single city | Coefficients are Mumbai-specific; no external validity test |
| 7 | HVI weights are judgement | Mitigated by sensitivity analysis + user-adjustable weights |
| 8 | Cloud gaps | Some cells rest on fewer observations; flag low-confidence cells |
| 9 | Static land cover (WorldCover 2021) | Land cover ages against multi-year LST composites |

A limitations section this specific is a strength in a viva — it demonstrates knowing what
the model does *not* say.

---

## 8. Reproducibility

Fixed random seeds · pinned dependency versions · pipeline regenerates `features.parquet`
from scratch · model artifacts carry a training-run manifest (date, git SHA, feature list,
metrics) · notebooks executed top-to-bottom before commit.
