# PROGRESS — UrbanHeat AI

Live task board. Newest phases get expanded into detailed tasks at their kickoff.

**Legend** `[ ]` todo · `[~]` in progress · `[x]` done · ✅ phase exit criterion
**Current phase:** 1 — Data pipeline
**Last updated:** 2026-07-20

---

## Phase 0 — Foundations · Week 1

**Goal:** repo, docs, accounts and environment in place; one Landsat image of Mumbai on screen.

### Repo & docs

- [X] git repo + GitHub remote (`DevGurav/urbanheat-mumbai`) + local identity
- [X] `.gitignore`, `.env.example`
- [X] `README.md`, `PROGRESS.md`, `LICENSE`
- [X] `docs/` tree: BLUEPRINT, conventions, architecture, data-dictionary, ml-methodology, api-reference, agents, runbook, devlog, references, CHANGELOG
- [X] ADR-0001 Earth Engine · ADR-0002 Gemini free tier · ADR-0003 no Redis/WebSockets · ADR-0004 files-then-Supabase · ADR-0005 LST target · ADR-0006 boosted trees
- [X] Folder scaffold: `data-pipeline/`, `backend/`, `frontend/`, `notebooks/`, `data/`, `models/`

### External prep — author's own accounts and installs

- [X] **Earth Engine noncommercial registration** — `urbanheat-mumbai`, academic / unpaid tier
- [X] **Google AI Studio** Gemini API key → `.env`
- [X] Python 3.11+ (via `uv`) — uv 0.11.29; project venv pinned to 3.12
- [X] Node.js LTS (needed Phase 5, install now) — v24.18.0, npm 11.13.0
- [ ] QGIS *(optional — inspecting rasters, report screenshots)*

### Environment

- [X] Python env with `earthengine-api`, `geemap`, `geopandas` — `pyproject.toml` + `uv.lock`,
  151 packages, `uv sync` reproduces it
- [X] `earthengine authenticate` succeeds — needed `--auth_mode=notebook` (`runbook.md` §6)

### Exit

- [X] ✅ **Hello-world notebook renders a Landsat LST image over Mumbai**
  — 56 scenes, both districts, min 29.0 / mean 39.8 / max 51.6 °C; interactive map,
  static PNG and the NDVI cross-check all render. **Phase 0 complete.**

---

## Phase 1 — Data pipeline · Weeks 2–4

**Goal:** one feature table describing every ~200 m cell of Mumbai. First presentable demo.

**Settled at kickoff, 2026-07-20**
Wards: Datameet `BMC_Wards.geojson`, CC BY 4.0, **24 administrative** wards (not the 227
electoral ones) · Grid: **200 m** (ADR-0007) · Season: Mar–May **2019–2026** ·
Package: `data_pipeline/`

### Pipeline scaffolding

- [X] Rename `data-pipeline/` → `data_pipeline/`; installable package (`python -m data_pipeline.run`)
- [X] `config.py` — `pydantic-settings` reading `.env`, replacing the notebook's `dotenv`
- [X] `ee_session.py` — one Earth Engine init shared by every stage
- [X] `run.py` — `--stage <name>`; each stage caches to `data/interim/` so a failure
  does not force a full rebuild (Earth Engine quota is finite — ADR-0001)

### Geometry — everything else joins to this

- [X] Fetch + validate BMC wards → `data/processed/wards.geojson`
  *(gate: exact set of 24 ward codes; measured 458 km², not the 603 km² the docs assumed)*
- [X] 200 m grid clipped to the ward union; **stable `cell_id`** from grid position, not row
  order — verified that dropping a ward renumbers none of the survivors
- [X] Ward label per cell by majority overlap → `data/interim/grid.parquet`
  *(11,944 cells, 458.3 km² land, reconciles with ward area to 0.01 km²)*

### Target variable

- [X] Promote the Phase 0 Landsat code into `sources/landsat.py`
- [X] Per-cell `lst_mean`, `lst_p90`, `lst_obs_count` → `data/interim/lst.parquet`
  *(mean 39.7 °C — matches Phase 0's 39.8 by a separate route; no cell cloud-starved,
  minimum 46 observations; park belt 3.15 °C cooler than the southern city)*
- [ ] `lst_trend` — slope of per-year Mar–May medians *(deferred — needs a separate per-year
  Landsat reduction; not required for the exit criterion. Build now or carry to Phase 2)*

### Predictors

- [X] Sentinel-2 → `ndvi_mean`, `ndvi_p10`, `ndbi_mean`, `ndwi_mean` → `data/interim/sentinel2.parquet`
  *(11,944 cells, 0 nulls; NDBI vs LST +0.74, NDVI vs LST −0.45 — premise holds. Reducer
  shared into `sources/_reduce.py`, Landsat refactor byte-identical)*
- [X] ESA WorldCover → per-class fractions per cell → `data/interim/worldcover.parquet`
  *(9 classes, not just tree/grass/built: mangrove is 10% of the city, crop is dry bare
  ground and the hottest class. built vs LST +0.59; water_fraction 0.96 on the low-NDVI
  cool cells resolves that ambiguity)*
- [X] WorldPop → `population`, `pop_density` → `data/interim/worldpop.parquet`
  *(year 2020; total 11.7 M reconciles with BMC's ~12.4 M. density vs built +0.74, vs LST
  +0.56 — the HVI premise: people are where the heat is. Densest cells = Dharavi, Parel)*
- [X] SRTM → `elevation_mean`, `slope_mean`; plus `dist_coast`, `dist_water` → `data/interim/terrain.parquet`
  *(elevation finds SGNP hills at 459 m; +4 °C sea-breeze gradient over the first 6 km,
  reversing in the park. cumulativeCost not fastDistanceTransform; sea = large connected water)*
- [X] OSM via OSMnx → `building_density`, `building_count`, `road_density`, `dist_park` → `data/interim/osm.parquet`
  *(80,842 buildings, cached in data/raw/. roads reliable (+0.69 vs built); buildings
  under-mapped (relative only); dist_park misleading — SGNP isn't OSM-tagged as park)*
- [X] Landsat optical → `albedo` (Liang 2001) → `data/interim/albedo.parquet`
  *(physically correct — sea 0.03, city median 0.13. 🚨 but albedo vs LST is +0.70 (wrong
  sign, land-cover confound): cool-roof lever must use a cited coefficient, not the model's)*
- [X] Neighbourhood aggregates → `ndvi_neigh_mean`, `built_neigh_mean` (queen contiguity via
  grid-index arithmetic; computed in the assembly step)
- [X] Open-Meteo join → `data/interim/weather.parquet`
  *(measured: air_temp vs LST +0.02 — near-zero within-city signal; only a coarse
  dist_coast proxy. Phase 2 has the evidence to drop it)*

### Assemble & verify

- [X] Join every source on `cell_id` → `data/processed/features.parquet`
  *(11,944 × 42 cols, GeoParquet — `assemble.py`, commit f67c8d8)*
- [X] **Validation gate:** row count, per-column null rate and observed range asserted for
  every feature — counts *and* magnitudes, the Phase 0 boundary lesson generalised.
  *(passed: 0 nulls in required columns, all 27 range-checked columns physical)*
- [X] Fill observed ranges in `docs/data-dictionary.md` — done for every source.
  *(§5: 6 of 9 questions closed; the 3 open — `land_fraction` model threshold, Open-Meteo
  survival, per-source reduction method — are Phase 2 decisions, tracked in §5)*
- [X] Exploration notebook: LST + NDVI maps, correlation matrix, ward summary table
  → `notebooks/01_explore_features.ipynb` (written, lint-clean, executes end-to-end with
  0 errors; committed without outputs)
- [X] ✅ **`features.parquet` exists and the notebook renders Mumbai's heat map**
  — `features.parquet` built (11,944×42); notebook verified to run. **Awaiting the author's
  visual confirmation of the heat map to tick this.**

---

## Phase 2 — ML: predict & explain · Weeks 5–7

- [ ] Baseline (linear) → XGBoost → LightGBM, spatial block cross-validation
- [ ] Metrics + model comparison → `docs/ml-methodology.md`
- [ ] SHAP: global importance + per-cell attribution
- [ ] Heat Vulnerability Index + ward hotspot ranking
- [ ] Scenario engine v1: `simulate(feature_deltas) → ΔLST`
- [ ] ✅ **Saved model + metrics; a greening scenario produces a sensible ΔLST map**

---

## Phase 3 — Backend API · Weeks 8–10

- [ ] FastAPI skeleton, settings, CORS, structured logging
- [ ] `/city/grid` `/hotspots` `/predict` `/explain/{cell_id}` `/scenario` `/weather` `/trends`
- [ ] Response caching + GeoJSON simplification/gzip
- [ ] ✅ **Everything demoable from Swagger `/docs` locally**

---

## Phase 4 — Agentic core · Weeks 11–14

- [ ] Services wrapped as LangChain tools
- [ ] RAG: knowledge-base PDFs → Chroma + local embeddings
- [ ] Agent 1 Urban AI Copilot · Agent 2 Planning Decision · Agent 3 Digital Twin · Agent 4 Monitoring
- [ ] LangGraph supervisor + rate-limit hygiene (backoff, cache, Groq fallback)
- [ ] GitHub Actions daily monitoring cron
- [ ] ✅ **Copilot answers a real planning question with real model numbers**

---

## Phase 5 — React dashboard · Weeks 15–19

- [ ] Vite + TS + MUI scaffold, API client, typed schemas
- [ ] Interactive map with layer toggles · Analytics views · Scenario simulator · Copilot chat · Alerts feed
- [ ] ✅ **Full end-to-end local demo**

---

## Phase 6 — Persistence, auth, deployment · Weeks 20–22

- [ ] Supabase schema (users, alerts, saved scenarios) + Auth
- [ ] Dockerize backend → Render · frontend → Vercel · secrets · CI
- [ ] ✅ **Public URLs work end-to-end**

---

## Phase 7 — Polish & academics · Weeks 23–24+

- [ ] PDF report endpoint (WeasyPrint) · demo script · screenshots
- [ ] Final report / paper draft · viva prep
- [ ] ✅ **Report draft complete from `docs/`**

---

## Parked ideas

Second city · SSE live alerts · Marathi/Hindi copilot replies · mobile layout ·
night-time LST from MODIS · air-quality layer (Sentinel-5P)

---

Session details: `docs/devlog.md` · Roadmap rationale: `docs/BLUEPRINT.md`
