# ADR-0005 — Land Surface Temperature as the model target

**Status:** Accepted
**Date:** 2026-07-17
**Phase:** 0

## Context

The system predicts "urban heat" at ~200 m resolution across Mumbai. What that phrase means
numerically is the single most consequential decision in the project — it determines the
training target, the achievable resolution, and what every downstream claim is allowed to
say. Two candidate targets exist, and they are not the same physical quantity.

**Air temperature (T_air, 2 m)** is what people experience and what heat-health thresholds
are written against. Mumbai has only a handful of IMD stations — roughly single digits
across ~600 km². **Land Surface Temperature (LST)** is the radiometric skin temperature of
the ground, measured directly by satellite thermal sensors for every pixel.

They correlate but diverge: asphalt at noon can read 50 °C+ LST while the air above it is
35 °C. The gap depends on wind, humidity, and surface type.

## Options considered

### A — Predict air temperature from station data

**Pros** Directly meaningful to a planner; comparable to weather reports; maps onto public
health heat thresholds without caveat.
**Cons** With <10 stations across the study area, a 20,000-cell model would be trained on
<10 independent labels. The model would be interpolating a handful of points using
satellite covariates — the "prediction" would be an artifact of the interpolation method,
and cross-validation would be meaningless (any held-out station is spatially unique). This
is not a data problem that more effort solves; the labels do not exist.

### B — Predict LST from satellite thermal bands

**Pros** Every one of the ~20k cells gets a directly measured label from Landsat 8/9
Collection-2 Level-2 (100 m thermal, resampled to 30 m, atmospherically corrected with QA);
the target varies at exactly the spatial scale the drivers do, which is what makes SHAP
attribution meaningful; multi-year composites give a real trend; this is the standard
target in the UHI remote-sensing literature, so results are comparable to published work
and the method is defensible under scrutiny.
**Cons** LST ≠ what people feel — every claim must be labelled *surface* temperature;
satellite overpass is ~10:30 local time, so this is mid-morning surface heat, not the 3 pm
peak or the night-time UHI that drives mortality; thermal band is 100 m native, so 200 m
cells are honest but 30 m claims would not be; clouds remove observations entirely.

### C — Hybrid: model LST, then statistically downscale to T_air using station data

**Pros** Ends with the quantity people care about; a recognised research direction.
**Cons** Inherits A's fatal flaw — the downscaling step is still calibrated against <10
stations; adds a whole research problem on top of an already six-month project; the error
bars on the final number would exceed the effect size being measured.

## Decision

**Option B — LST from Landsat 8/9 Collection-2 Level-2, dry-season (Mar–May) multi-year
median composites.**

The deciding factor is label availability. A supervised model needs labels at the
resolution of its claims; only LST provides them. Option A would produce a model that looks
sophisticated and is really an interpolation of nine points, which is the kind of thing that
collapses under one pointed question. Option C's downscaling step is an entire separate
research project.

The LST→T_air gap is handled by **stating it**, not hiding it: every UI label, API field and
report figure says *surface temperature*, and the limitation is documented explicitly in
`ml-methodology.md`. This is more defensible than a fabricated air-temperature number.

Mar–May is forced by Mumbai's monsoon — Jun–Sep optical and thermal imagery is unusable
under cloud, and it is also the season when heat action actually matters.

## Consequences

**Positive**
- ~20k directly measured labels instead of <10 interpolated ones; cross-validation means
  something.
- Comparable to the published UHI literature → methodology is defensible and citable.
- Multi-year compositing yields a genuine trend layer.
- Scenario simulation is coherent: perturbing NDVI/albedo changes surface energy balance,
  which is precisely what LST measures.

**Negative**
- All outputs are surface temperature and must be labelled as such — a standing rule for
  UI copy, API schemas and report figures.
- Mid-morning snapshot only; the night-time UHI (the health-critical one) is out of scope.
- Dry-season only; no monsoon or winter picture.
- The Heat Vulnerability Index built on LST is a *relative* prioritisation tool, not an
  absolute health-risk score. It must never be presented as the latter.
- Cloud-contaminated cells need masking and may leave gaps; multi-year median compositing
  is the mitigation.

**Revisit if** a dense low-cost sensor network for Mumbai becomes available (some Indian
cities are deploying them) — that would make option C viable as a follow-on layer without
invalidating any of this work, since LST would remain the intermediate variable.

**Follow-on** MODIS night-time LST is parked as a future layer: 1 km resolution is too
coarse for the main grid, but it would add the night-time dimension the report will
correctly list as missing.
