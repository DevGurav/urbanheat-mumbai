# PROGRESS — UrbanHeat AI

Live task board. Newest phases get expanded into detailed tasks at their kickoff.

**Legend** `[ ]` todo · `[~]` in progress · `[x]` done · ✅ phase exit criterion
**Current phase:** 1 — Data pipeline
**Last updated:** 2026-07-20

---

## Phase 0 — Foundations · Week 1

**Goal:** repo, docs, accounts and environment in place; one Landsat image of Mumbai on screen.

### Repo & docs
- [x] git repo + GitHub remote (`DevGurav/urbanheat-mumbai`) + local identity
- [x] `.gitignore`, `.env.example`
- [x] `README.md`, `PROGRESS.md`, `LICENSE`
- [x] `docs/` tree: BLUEPRINT, conventions, architecture, data-dictionary, ml-methodology, api-reference, agents, runbook, devlog, references, CHANGELOG
- [x] ADR-0001 Earth Engine · ADR-0002 Gemini free tier · ADR-0003 no Redis/WebSockets · ADR-0004 files-then-Supabase · ADR-0005 LST target · ADR-0006 boosted trees
- [x] Folder scaffold: `data-pipeline/`, `backend/`, `frontend/`, `notebooks/`, `data/`, `models/`

### External prep — author's own accounts and installs
- [x] **Earth Engine noncommercial registration** — `urbanheat-mumbai`, academic / unpaid tier
- [x] **Google AI Studio** Gemini API key → `.env`
- [x] Python 3.11+ (via `uv`) — uv 0.11.29; project venv pinned to 3.12
- [x] Node.js LTS (needed Phase 5, install now) — v24.18.0, npm 11.13.0
- [ ] QGIS *(optional — inspecting rasters, report screenshots)*

### Environment
- [x] Python env with `earthengine-api`, `geemap`, `geopandas` — `pyproject.toml` + `uv.lock`,
      151 packages, `uv sync` reproduces it
- [x] `earthengine authenticate` succeeds — needed `--auth_mode=notebook` (`runbook.md` §6)

### Exit
- [x] ✅ **Hello-world notebook renders a Landsat LST image over Mumbai**
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
- [x] Rename `data-pipeline/` → `data_pipeline/`; installable package (`python -m data_pipeline.run`)
- [x] `config.py` — `pydantic-settings` reading `.env`, replacing the notebook's `dotenv`
- [x] `ee_session.py` — one Earth Engine init shared by every stage
- [x] `run.py` — `--stage <name>`; each stage caches to `data/interim/` so a failure
      does not force a full rebuild (Earth Engine quota is finite — ADR-0001)

### Geometry — everything else joins to this
- [x] Fetch + validate BMC wards → `data/processed/wards.geojson`
      *(gate: exact set of 24 ward codes; measured 458 km², not the 603 km² the docs assumed)*
- [x] 200 m grid clipped to the ward union; **stable `cell_id`** from grid position, not row
      order — verified that dropping a ward renumbers none of the survivors
- [x] Ward label per cell by majority overlap → `data/interim/grid.parquet`
      *(11,944 cells, 458.3 km² land, reconciles with ward area to 0.01 km²)*

### Target variable
- [x] Promote the Phase 0 Landsat code into `sources/landsat.py`
- [x] Per-cell `lst_mean`, `lst_p90`, `lst_obs_count` → `data/interim/lst.parquet`
      *(mean 39.7 °C — matches Phase 0's 39.8 by a separate route; no cell cloud-starved,
      minimum 46 observations; park belt 3.15 °C cooler than the southern city)*
- [ ] `lst_trend` — slope of per-year Mar–May medians

### Predictors
- [x] Sentinel-2 → `ndvi_mean`, `ndvi_p10`, `ndbi_mean`, `ndwi_mean` → `data/interim/sentinel2.parquet`
      *(11,944 cells, 0 nulls; NDBI vs LST +0.74, NDVI vs LST −0.45 — premise holds. Reducer
      shared into `sources/_reduce.py`, Landsat refactor byte-identical)*
- [ ] ESA WorldCover → tree / grass / built / water fractions per cell
- [ ] WorldPop → `population`, `pop_density`
- [ ] SRTM → `elevation_mean`, `slope_mean`; plus `dist_coast`, `dist_water`
- [ ] OSM via OSMnx → `building_density`, `building_count`, `road_density`, `dist_park`
- [ ] Landsat optical → `albedo` (Liang 2001) — the cool-roof lever
- [ ] Neighbourhood aggregates → `ndvi_neigh_mean`, `built_neigh_mean`
- [ ] Open-Meteo join *(expected near-constant at 11 km; Phase 2 decides if they stay)*

### Assemble & verify
- [ ] Join every source on `cell_id` → `data/processed/features.parquet`
- [ ] **Validation gate:** assert row count, per-column null rate and observed range for
      every feature. Counts *and* magnitudes, never just non-emptiness — a silent partial
      join is the Phase 0 boundary bug at 15,000× the scale, with no printed area to catch it
- [ ] Fill observed ranges in `docs/data-dictionary.md`; close remaining §5 questions
- [ ] Exploration notebook: LST + NDVI maps, correlation matrix, ward summary table
- [ ] ✅ **`features.parquet` exists and the notebook renders Mumbai's heat map**

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
