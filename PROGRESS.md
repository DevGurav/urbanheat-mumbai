# PROGRESS — UrbanHeat AI

Live task board. Newest phases get expanded into detailed tasks at their kickoff.

**Legend** `[ ]` todo · `[~]` in progress · `[x]` done · ✅ phase exit criterion
**Current phase:** 0 — Foundations
**Last updated:** 2026-07-19

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
- [ ] ✅ **Hello-world notebook renders a Landsat LST image over Mumbai**
      — ran end to end: 56 scenes, both districts, min 29.0 / mean 39.8 / max 51.6 °C,
      interactive map and static PNG both rendered. Awaiting the author's visual check of
      the LST/NDVI inverse relationship before this is ticked

---

## Phase 1 — Data pipeline · Weeks 2–4

**Goal:** one feature table describing every ~200 m cell of Mumbai. First presentable demo.

- [ ] Mumbai boundary + BMC ward polygons → `data/processed/wards.geojson`
- [ ] ~200 m analysis grid over the city boundary, stable `cell_id`
- [ ] Landsat 8/9 L2 dry-season (Mar–May) LST composites, multi-year → target variable
- [ ] Sentinel-2 NDVI / NDBI / NDWI composites
- [ ] ESA WorldCover land-cover fractions per cell
- [ ] WorldPop population density per cell
- [ ] SRTM elevation + distance-to-coast
- [ ] OSM building density, road density, park proximity (OSMnx)
- [ ] Open-Meteo historical weather join
- [ ] Assemble `data/processed/features.parquet`; fill `docs/data-dictionary.md`
- [ ] Exploration notebook: LST + NDVI maps, correlation matrix, ward summary
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
