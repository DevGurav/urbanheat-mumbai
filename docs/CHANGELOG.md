# Changelog

Milestone history. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
An entry lands when a **phase completes** (its ✅ exit criterion is verified) — session
detail belongs in [devlog.md](devlog.md).

---

## Phase 2 — ML: predict & explain · completed 2026-07-26

### Added
- `data_pipeline/ml/` — `dataset` (X/y/ward-groups under ADR-0008), `cv` (ward-grouped spatial
  CV + naive contrast), `train` (the model ladder), `explain` (SHAP + physics gate), `hvi`
  (Heat Vulnerability Index), `scenario` (the digital twin)
- Trained **XGBoost** LST model → `models/model.joblib` + `model_meta.json`; SHAP global
  importance + per-cell attribution → `models/shap_*`
- `data/processed/hvi.parquet` (HVI + hotspot rank) and `data/processed/scenario_greening.parquet`
  (a demonstration greening + cool-roof ΔLST map)
- ADR-0008 (spatial CV, training set, feature policy); intervention-coefficient literature
  logged in `references.md`; pytest suite grown to 37 tests

### Verified
- ✅ **Exit criterion met** — saved model + metrics, and a greening scenario produces a sensible
  ΔLST map. The model predicts an *unseen ward's* surface temperature to **1.10 °C** (spatial
  R² 0.893); the small random-vs-spatial gap (0.047) confirms it learned physical drivers, not
  location. The SHAP physics gate passes on every load-bearing driver. The HVI ward ranking is
  robust to its weights (top-10 stable 9–10/10, Spearman ρ ≥ 0.98). Greening cools 7,410 cells
  (mean −0.65 °C, best −4.88 °C), concentrated in the hot dense wards.

### Known limitations carried into Phase 3
- **Cool-roof ΔLST uses a cited coefficient (Li et al. 2014), not the model** — the albedo
  confound (ADR-0008); the one lever that would have silently backfired through the model.
- Greening warmed 482 off-manifold cells (high built *and* high NDVI, rare in training); ΔLST is
  floored at 0 and the count reported. The principled v2 is a monotone-constrained model.
- Scenario outputs are correlational ("cells like this, but greener, are ~X cooler"), not causal;
  the model has no feedback effects between cells.

---

## Phase 1 — Data pipeline · completed 2026-07-21

### Added
- `data_pipeline/` package: `config` (pydantic-settings), `ee_session` (one EE init),
  `run.py` stage orchestrator that caches per-stage and skips completed stages
- Geometry — BMC ward boundaries (DataMeet, 24 administrative wards) →
  `data/processed/wards.geojson`; a 200 m grid with a **position-derived, permanent `cell_id`**
  → `data/interim/grid.parquet` (11,944 cells, ADR-0007)
- Target — Landsat 8/9 C2 L2 dry-season LST per cell (`lst_mean`, `lst_p90`, `lst_obs_count`)
- Eight predictor sources → `data/interim/*.parquet`: Sentinel-2 (NDVI/NDBI/NDWI),
  ESA WorldCover (9 land-cover fractions), WorldPop (population/density), SRTM + surface-spread
  distances (elevation/slope/dist_coast/dist_water), OSM (building/road/park), Landsat albedo
  (Liang 2001), Open-Meteo weather; plus neighbourhood aggregates
- `data/processed/features.parquet` — **11,944 rows × 42 columns**, assembled from every
  source with a validation gate (row count, null rate, physical range per column)
- `notebooks/01_explore_features.ipynb` — heat map, LST/NDVI inverse, driver correlations,
  ward summary
- ADR-0007 — 200 m analysis grid

### Verified
- ✅ **Exit criterion met** — `features.parquet` exists and the notebook renders Mumbai's heat
  map. The premise holds in the data: `ndbi_mean` +0.74 and the built/population cluster warm,
  mangrove/water/NDVI (~−0.46) cool, and two independent satellites agree at ward level. Study
  area **458 km²**; total population **11.7 M** (reconciles with BMC's ~12.4 M census).

### Known limitations carried into Phase 2
- **Albedo confound** — correlates +0.70 with LST (wrong sign, land-cover confound); the
  cool-roof lever must use a cited coefficient, not the model's (`ml-methodology.md` §6)
- OSM buildings under-mapped (relative indicator only); `dist_park` misleading (SGNP is not
  OSM-tagged as a park)
- Weather covariates carry near-zero within-city signal — a Phase 2 drop candidate
- `land_fraction` model threshold undecided (Phase 2); `lst_trend` deferred (its per-year
  reduction is not built)

---

## Phase 0 — Foundations · completed 2026-07-20

### Added
- Repository scaffolding: `.gitignore`, `.env.example`, `README.md`, `LICENSE` (MIT, with
  data-source attributions)
- `PROGRESS.md` — phase task board with exit criteria
- `docs/BLUEPRINT.md` — 8-phase roadmap, scope, risk register, free-tier stack map
- `docs/conventions.md` — hard rules (zero-cost, secrets, data discipline), Definition of
  Done, code and documentation conventions
- `docs/architecture.md` — component, pipeline, request-flow and deployment diagrams
  (Mermaid)
- `docs/data-dictionary.md` — source datasets, target, feature specification, leakage watch
- `docs/ml-methodology.md` — model progression, spatial block CV strategy, HVI design,
  scenario engine limits
- `docs/agents.md` — four-agent design, toolbelt, guardrails, rate-limit strategy
- `docs/api-reference.md` — planned endpoint contracts
- `docs/runbook.md` — external prep, setup, demo checklist, troubleshooting
- `docs/references.md` — datasets, methods, reading list
- `docs/devlog.md` — engineering journal
- ADR-0001 — Google Earth Engine for satellite data
- ADR-0002 — Gemini Flash free tier as the LLM
- ADR-0003 — Drop Redis and WebSockets from the MVP
- ADR-0004 — Files first, Supabase later
- ADR-0005 — Land Surface Temperature as the model target
- ADR-0006 — Gradient-boosted trees over deep learning

- Monorepo folder scaffold: `data-pipeline/`, `backend/`, `frontend/`, `notebooks/`,
  `data/`, `models/`, `.github/workflows/`
- Python environment: `pyproject.toml` + `uv.lock`, pinned to 3.12 via `.python-version`.
  `uv sync` reproduces it from scratch
- `notebooks/00_hello_earth_engine.ipynb` — authenticates Earth Engine, loads the Mumbai
  boundary, and renders a cloud-masked dry-season Landsat 8/9 surface-temperature composite.
  Documents the Collection 2 Level-2 scale factors and `QA_PIXEL` cloud masking in detail
- Earth Engine noncommercial registration (`urbanheat-mumbai`, academic tier); Gemini API key

### Verified
- ✅ **Exit criterion met** — Landsat surface-temperature image of Mumbai renders in a
  notebook. 56 scenes over Mar–May 2019–2025; min 29.0 °C, mean 39.8 °C, max 51.6 °C across
  a land-only footprint. Numbers checked before the map was trusted.

### Known limitations carried into Phase 1
- City boundary comes from FAO GAUL, which measures Greater Mumbai at 487 km² against BMC's
  published 603 km² (−19%) and carries redistribution restrictions. Replaced by BMC ward
  polygons in Phase 1
- Surface temperature only, at ~10:30 local overpass. Not air temperature, not the afternoon
  peak, not the night-time heat island (ADR-0005)

---

<!--
Phase entries get released as versions once the project is deployable:
  Phase 1 → 0.1.0  data pipeline
  Phase 2 → 0.2.0  ML + explainability
  Phase 3 → 0.3.0  backend API
  Phase 4 → 0.4.0  agents
  Phase 5 → 0.5.0  dashboard
  Phase 6 → 1.0.0  public deployment
  Phase 7 → 1.1.0  reports + polish
-->
