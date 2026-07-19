# ADR-0007 — 200 m analysis grid

**Status:** Accepted
**Date:** 2026-07-20
**Phase:** 1

## Context

The model predicts surface temperature per grid cell. Cell size decides three things at
once: how many training rows exist, the finest spatial claim the project is entitled to
make, and how much averaging smooths sensor noise before the model ever sees it.

It is effectively irreversible. `cell_id` is the join key across the pipeline, the model,
the API and any saved scenario, and `conventions.md` forbids reindexing it. Changing
resolution later is a pipeline rebuild, not a parameter change.

**The resolution that matters is not the one in the file.** Landsat 8/9 Collection 2
Level-2 delivers `ST_B10` on the 30 m product grid, but the thermal instrument's native
resolution is **100 m** — the 30 m is packaging, not information. Treating the delivered
grid as the true resolution is the standard way to over-claim in LST work, and it is
invisible in the output because a 30 m map renders perfectly happily.

Study area: Greater Mumbai (BMC), ~603 km².

## Options considered

### A — 100 m, matching native thermal

**Pros** Maximum retained detail; aligns exactly with WorldPop's 100 m grid; ~60,000 cells
is still tractable for boosted trees; no information discarded by aggregation.
**Cons** One thermal pixel per cell means **zero averaging** — per-pixel radiometric noise
and any co-registration error pass undiluted into the target variable. Roughly 4× the
OSM/Overpass and per-cell reduction work of option B. And sitting exactly at the sensor's
limit is a harder position to defend than sitting deliberately above it: "why exactly at
native resolution?" invites the follow-up "so what is your error budget per pixel?"

### B — 200 m

**Pros** ~15,000 cells, each averaging ~4 native thermal pixels, which damps per-pixel
noise. Sits **2× coarser than native**, so no spatial claim exceeds what the instrument
measured — the safe direction. ~15k rows against ~25 features is the right order for
gradient-boosted trees (ADR-0006): enough to fit, small enough that spatial block CV is
cheap. Matches the figure already written into `BLUEPRINT.md` and `data-dictionary.md`.
**Cons** Sub-block detail disappears — a single shaded courtyard or one cool-roofed
building does not register. Ward-internal variation is coarser than a street-level planner
might want.

### C — 300 m

**Pros** ~6,700 cells, smoothest per-cell estimates, most conservative possible claim.
**Cons** Halves the training set. Blurs contrasts at precisely the scale urban
interventions happen — a neighbourhood park or a block of cool roofs is a ~200 m object,
and averaging it into a 300 m cell dilutes the very effect the scenario engine exists to
estimate. There is no principled reason to go this coarse when native thermal is 100 m.

## Decision

**200 m.**

The deciding factor is the *direction* of the resolution claim. At 200 m every cell is an
aggregate of measured pixels, so the project never asserts detail finer than the instrument
delivered — that is defensible without qualification. Option A sits exactly at the sensor's
limit, where noise and geolocation error have nowhere to average out. Option C throws away
real signal at the scale interventions actually operate.

The secondary factor is sample size. ~15,000 rows is comfortable for tree ensembles on ~25
features, and leaves enough data for spatial block cross-validation to hold out whole
regions without starving the training folds (`ml-methodology.md` §2).

## Consequences

**Positive**
- Every spatial claim is defensible by construction: coarser than native thermal.
- ~4× averaging per cell suppresses per-pixel thermal noise in the target.
- ~15k rows fit comfortably in memory; blocked CV is cheap.
- No documentation churn — `BLUEPRINT.md` and `data-dictionary.md` already say ~200 m.

**Negative**
- **Sub-block features are invisible.** The scenario engine therefore operates on
  cell-average interventions ("raise NDVI across this cell"), never on individual
  buildings. This must be stated whenever scenario results are presented — claiming a
  per-building effect from a 200 m model would be a fabrication.
- 200 m aligns to no source's native grid (100 m thermal, 10 m WorldCover and Sentinel-2,
  30 m SRTM, 100 m WorldPop). Every source is resampled or area-weighted into the cell, and
  the reduction method per source has to be recorded in `data-dictionary.md` rather than
  left implicit.
- `cell_id` is fixed at this resolution permanently. Any later change invalidates every
  saved scenario, every stored model and any cached API response.

**Revisit if** the target moves to an instrument with materially finer thermal resolution
(ECOSTRESS is ~70 m), or if Phase 2 shows the model systematically under-fitting because
within-cell heterogeneity dominates the residuals. In either case the honest response is a
finer grid **and** a re-derived `cell_id` — a pipeline rebuild under a superseding ADR, not
a patch to this one.
