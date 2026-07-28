# ADR-0008 — Spatial cross-validation, training set, and feature policy

**Status:** Accepted
**Date:** 2026-07-26
**Phase:** 2

## Context

Phase 1's feature table showed strong spatial autocorrelation: the neighbourhood aggregates
correlate with LST almost as strongly as a cell's own value (`built_neigh_mean` +0.60 vs
`built_fraction` +0.59; `ndvi_neigh_mean` −0.43 vs `ndvi_mean` −0.45). Adjacent 200 m cells
are therefore near-duplicates. Three coupled choices decide whether the model's reported
performance is honest or an artefact — they are settled together because they interact.

The failure mode they guard against is the one in the risk register: a model that looks
sophisticated, scores a high R², and is really memorising spatial position — worthless but
impressive, and the kind of thing that collapses under one pointed question.

## Options considered & decisions

### 1. Cross-validation split — **ward-grouped k-fold**

**Random k-fold** would place near-duplicate neighbouring cells in both train and test,
inflating R² by leaking autocorrelation (`ml-methodology.md` §2, Roberts et al. 2017).
Rejected outright. **Spatial block grid** (~5 km squares) is the canonical alternative but
adds a block-size parameter to justify and cuts across ward lines. **Spatial k-means** on
centroids is flexible but non-standard and harder to defend.

**Decision: `GroupKFold` on `ward_code`** — hold out whole BMC wards. It answers the question
a planner actually asks ("can this predict a ward it has never seen?"), it is the unit the
project aggregates to, and it blocks adjacent-cell leakage cleanly. 24 wards → ~5 folds.
**Cost:** wards vary in size, so folds are uneven — accepted as honest.

### 2. Training set — **`land_fraction ≥ 0.5`**

A cell that is mostly sea carries water temperature, not urban heat; Phase 1 measured a
monotonic LST-vs-`land_fraction` gradient (33.7 °C below 0.1 land → 40.1 °C fully inland).
Training on those cells would teach the model land→heat relationships from water pixels.

**Decision: train and evaluate on `land_fraction ≥ 0.5`** (~11.5k of 11,944 cells); predict
and display on all land cells. **All cells** was rejected (contaminated target); **≥ 0.9** was
rejected as discarding partial-coast cells the model can still learn from.

### 3. Feature policy — **exclude absolute location**

Given raw coordinates, gradient-boosted trees will fit a spatial surface — memorising *where*
the hot areas are — instead of the causal drivers. That weakens SHAP (it credits "location"
rather than NDBI or albedo) and makes the scenario engine incoherent: you cannot "move" a cell
to cool it.

**Decision: drop `ward_code`, `centroid_lat`, `centroid_lon` from the feature matrix.** The
neighbourhood aggregates (`ndvi_neigh_mean`, `built_neigh_mean`) already supply legitimate
spatial context without absolute position. Also **hard-excluded as target leakage**, not a
preference: `lst_p90` and `lst_obs_count` (both derived from the same thermal band as the
target) and `wc_pixels` (a QA count).

## Consequences

**Positive**
- Reported metrics are honest spatial-generalisation estimates, not autocorrelation artefacts.
- SHAP attributes heat to physical drivers, which is what the recommendation layer stands on.
- The scenario engine is coherent — every feature it perturbs is something an intervention can
  actually change.

**Negative**
- Spatial-CV R² will read **lower** than a random split would report. This is expected and is
  the honest number; the project's framing (ADR-0006) is that a weak-but-honest model with good
  SHAP still carries the work.
- Ward-grouped folds are uneven in size.
- Excluding location forgoes any real signal that has no causal proxy — accepted as the price
  of a defensible causal story.

**Revisit if** a second city needs a finer spatial-block scheme, or if diagnostics show the
location exclusion is discarding signal with no physical proxy (unlikely — the neighbourhood
aggregates cover most of it).
