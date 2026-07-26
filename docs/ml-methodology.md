# ML Methodology

The modelling design, the validation strategy, and the honest limitations. This document
becomes the methodology chapter of the final report.

**Status:** design, written before implementation. Sections marked *[Phase 2]* get filled
with real numbers as the work lands. **No result is recorded here until it is measured.**

---

## 1. Problem statement

**Task** Supervised regression.
**Unit** One 200 m grid cell of Greater Mumbai (≈11–12k cells; ADR-0007).
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

**The fix — ward-grouped spatial cross-validation (settled, ADR-0008).** `GroupKFold` on
`ward_code`: hold out **whole BMC wards** (24 → ~5 folds), so no held-out cell has a neighbour
in training. Chosen over a k-km block grid (an extra parameter, cuts across wards) and k-means
clusters (non-standard) because wards are the unit recommendations are made in and the question
a planner asks — *predict a ward it has never seen?* Wards are uneven in size; accepted as
honest.

**Training set and features (ADR-0008).** Train and evaluate on `land_fraction ≥ 0.5` (mostly-
sea cells carry water temperature); predict on all land cells. Exclude absolute location
(`ward_code`, `centroid_lat/lon`) so the trees learn causal drivers, not a memorised spatial
surface — which keeps SHAP meaningful and the scenario engine coherent. Hard-exclude the
target-leakage columns `lst_p90`, `lst_obs_count` (both from the thermal band) and the QA
count `wc_pixels`.

**Both numbers get reported.** Naive random-split CV alongside blocked CV. The gap between
them is a finding, not an embarrassment — it quantifies how much of an apparently good
score is autocorrelation. Reporting only the blocked (lower, honest) number without the
contrast wastes the insight.

**Measured (Phase 2, XGBoost).** Naive (random-split) R² **0.941** · blocked (ward-grouped) R²
**0.893** · gap **+0.047**. The gap is *small* — and that is the point: because absolute
location is excluded (ADR-0008) the model cannot memorise the map, so it generalises to unseen
wards almost as well as to random cells. A large gap would have meant the score was mostly
autocorrelation; a small one means the 0.893 is real skill from physical drivers.

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

**Results (Phase 2 — ward-grouped 5-fold spatial CV; naive = random 5-fold).**

| Model | naive R² | spatial R² | spatial RMSE °C | spatial MAE °C | fit |
|---|---|---|---|---|---|
| mean floor | −0.00 | −0.09 | 3.54 | 2.77 | 0.4 s |
| ridge | 0.854 | 0.815 | 1.45 | 1.13 | 0.2 s |
| random forest | 0.925 | 0.882 | 1.15 | 0.88 | 72 s |
| **XGBoost** ✓ | 0.941 | **0.893** | **1.10** | 0.85 | 12 s |
| LightGBM | 0.939 | 0.893 | 1.10 | 0.85 | 6 s |

**Selected: XGBoost** on best spatial RMSE (1.10 °C), tied with LightGBM on R² 0.893 — it
predicts an unseen ward's surface temperature to ~1.1 °C from physical drivers alone. Saved to
`models/model.joblib` with `model_meta.json` (feature list, all metrics, CV scheme). The mean
floor is *negative* under spatial CV — a held-out ward's temperature differs from the training
mean, which is exactly the ward-to-ward variation the blocked split is meant to expose.

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

**Measured (Phase 2, `data_pipeline/ml/explain.py`).** `mean |SHAP|` ranks `ndbi_mean`
first (1.41 °C), then `albedo` (0.51), `pop_density` (0.37), `built_fraction` (0.36),
`ndvi_neigh_mean` (0.33), `dist_coast` (0.29) — vegetation, built-up and coast dominate, as
expected for Mumbai.

The gate is enforced on the **load-bearing drivers only** (NDBI, built, built-neigh, pop
density, NDVI, NDVI-neigh, tree, water) — all eight pass with the physically correct sign. It
is *not* enforced on collinear/low-importance features, whose SHAP sign is credit-shared with a
stronger same-direction driver and therefore unreliable: `building_density`/`road_density` come
out "cool" (their warming credit is absorbed by `built_fraction`/`ndbi_mean`), and `ndvi_p10`/
`mangrove_fraction` come out "warm" (absorbed by `ndvi_mean`/`water_fraction`). These are
reported as credit-sharing, not failures — gating them would be a false alarm. **`albedo` comes
out warm as predicted (ADR-0008): the confound, not a bug.** Per-cell SHAP is written to
`models/shap_values.parquet` for `/explain/{cell_id}`.

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

**Measured (Phase 2, `data_pipeline/ml/hvi.py`).** Most-vulnerable wards at the base weights:
**B, L, C, H/E, F/S, K/E, G/N (Dharavi), E** — the dense, hot wards, matching the "hot AND
dense" cells identified in Phase 1. **The sensitivity check passes decisively:** across five
weight variants (heat-heavy, exposure-heavy, equal, green-heavy, heat+exposure-only) the top-10
ward ranking holds at **9–10/10 overlap with Spearman ρ ≥ 0.98**. The ranking does not flip
under reasonable re-weighting, so the index is robust enough to publish. Written to
`data/processed/hvi.parquet` (kept out of the model's feature table — it is derived from the
target `lst_mean`, so using it as a feature would be leakage).

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

| Intervention | Feature changes | Mechanism / source |
|---|---|---|
| **Urban forestry / greening** ✅ | `ndvi_mean` ↑ (toward 0.4), `ndvi_neigh_mean` ↑ | **through the model** — NDVI cooling is SHAP-validated; magnitude corroborated by Grover & Singh (2015), ~1.39 °C/unit NDVI |
| **Cool / reflective roofs** ✅ | `albedo` ↑ on the built area | **cited coefficient, NOT the model** (albedo confound, ADR-0008) — Li et al. (2014): ΔLST = −(1.7/0.5)·`built_fraction`·coverage |
| Green roofs | `ndvi_mean` ↑, `built_fraction` unchanged | *[future]* |
| Water body / restoration | `ndwi_mean` ↑, `dist_water` ↓ | *[future]* |
| Depaving / permeable surfaces | `impervious_fraction` ↓, `ndvi_mean` ↑ | *[future]* |

🚨 **`albedo` is confounded and must not use the model's own coefficient.** Phase 1 measured
`albedo` correlating **+0.70** with `lst_mean` in the observational data — brighter reads
*hotter*, because dark water is cool and bright bare/built is hot (`data-dictionary.md`, albedo
caveat). A model trained on this learns a positive albedo→LST coefficient, so raising albedo in
the twin would predict **warming** and the cool-roof recommendation would backfire. The cool-roof
ΔLST **must** come from a cited albedo-cooling study, never from the model's learned coefficient,
and the physics gate below must treat a positive albedo SHAP as expected confounding, not a
model bug. This is the one intervention where the data's sign is actively wrong.

**Measured (Phase 2, `data_pipeline/ml/scenario.py`).** A city-wide greening scenario (raise
every cell below NDVI 0.4 toward it, re-predict through the model, clamp to the envelope) cools
**7,410 cells, mean −0.65 °C, best −4.88 °C**, concentrated in the hot dense grey wards
(B −1.49, C −1.13, L −1.05) — the map is sensible and targets exactly where greening helps most.
The cool-roof lever (cited Li et al. coefficient) gives mean −1.38 °C, best −3.40 °C over built
cells. Written to `data/processed/scenario_greening.parquet`.

⚠️ **Greening is floored at ΔLST ≤ 0.** The correlational tree model predicted small *spurious*
warming for 482 cells where raising NDVI pushed them off the training manifold (high built
fraction *and* high NDVI, rare in the data). Greening cannot warm a cell all-else-equal, so the
delivered map floors at zero and reports the floored count. The principled v2 fix is a
monotone-constrained model (NDVI forced monotonically cooling); the floor is the honest interim.

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
