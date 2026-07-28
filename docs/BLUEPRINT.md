# BLUEPRINT — UrbanHeat AI

Master roadmap. Task-level state lives in [`PROGRESS.md`](../PROGRESS.md); this document
explains the *shape* of the project and why it is built this way.

---

## 1. The problem

Mumbai's dense built-up wards run several degrees hotter than its green and coastal ones.
The gap is invisible in the weather report — official temperature comes from a handful of
station points, while the heat that actually harms people varies street by street with
concrete, tree cover and roof colour. Planners therefore lack two things:

1. **A spatial picture** of where heat concentrates and *why* it concentrates there.
2. **A way to test interventions** before committing budget — does greening this ward
   beat coating roofs in that one?

This project supplies both, from open data, and puts a natural-language interface on top
so the answer is reachable without GIS training.

## 2. The approach in one paragraph

Divide Mumbai into a 200 m grid (~11–12k cells). For each cell, derive predictors from
free satellite and open data: vegetation (NDVI), built-up index (NDBI), water (NDWI),
albedo, land-cover fractions, building and road density, population, elevation, distance
to coast. Take **Land Surface Temperature** from Landsat 8/9 thermal bands as the target.
Train gradient-boosted trees to predict LST from the predictors; use SHAP to attribute
each cell's temperature to its causes. Rank priorities by a Heat Vulnerability Index that
weighs heat against population and lack of green cover. The **digital twin** is the same
model run backwards-ish: perturb a cell's features (more trees → higher NDVI; cool roofs →
higher albedo) and re-predict to get a ΔLST map. Four agents wrap this engine so a planner
can ask for it in English. This is established UHI methodology — the contribution is the
agentic interface and the end-to-end mitigation loop, not new remote sensing.

### Why LST and not air temperature

Air temperature at 2 m is what people feel, but Mumbai has too few stations to train a
200 m model — the target would be interpolation, not measurement. LST is measured directly
by satellite at 100 m (resampled 30 m) for every cell, which is what makes a spatial model
possible at all. LST and air temperature are correlated but **not interchangeable**;
surfaces run hotter than the air above them. Every output is therefore labelled as
*surface* temperature, and this is stated as a limitation rather than glossed over.

## 3. Scope

**In scope** Mumbai (BMC boundary) · dry season (Mar–May) · surface temperature ·
multi-year composites for trend · four agents · one dashboard · public deployment.

**Out of scope, deliberately** Real-time satellite ingestion (Landsat revisits every
16 days — "real-time" is weather, not imagery) · air-temperature downscaling ·
street-level (<100 m) resolution · other cities (see Parked ideas) · mobile app.

**Cut from the original architecture** — justified in the report as production
considerations rather than pretended-at: Redis (in-process cache + GitHub Actions cron
replace it), WebSockets (polling suffices at this scale), S3 object storage (files +
Supabase storage), full RBAC (single planner role).

## 4. Constraints

| Constraint | Consequence |
|---|---|
| **₹0 budget, hard** | Every service on a free tier; see [decisions/](decisions/) for each pick |
| No GPU | Model must be tree-based on a ~20k-row table, not deep learning on rasters |
| Laptop-scale RAM | Heavy raster math stays server-side in Earth Engine; only aggregates come down |
| Author is sole developer, intermediate | Prefer boring, explainable tech; every phase must end in something demoable |
| Fully explainable | Author must be able to explain every line and every number |

## 5. Free-tier stack map

Original architecture component → what is actually used, and what it costs.

| Component | Choice | Cost |
|---|---|---|
| Satellite data | Earth Engine Python API, noncommercial registration | ₹0 |
| Weather | Open-Meteo (keyless; historical + forecast) | ₹0 |
| Land cover / population / elevation | ESA WorldCover, WorldPop, SRTM — all in the GEE catalog | ₹0 |
| OSM features | OSMnx + Overpass | ₹0 |
| ML + explainability | scikit-learn, XGBoost, LightGBM, SHAP — trained locally | ₹0 |
| Backend | FastAPI + Uvicorn + Pydantic | ₹0 |
| Orchestration + LLM | LangGraph + Gemini Flash free tier (no fallback provider — ADR-0011) | ₹0 |
| Embeddings | Gemini `gemini-embedding-001` API (ADR-0013 — local `sentence-transformers` cost too much RAM for Render's free tier) | ₹0 |
| Vector DB | ChromaDB embedded, persisted to disk | ₹0 |
| Relational + spatial DB | Files/SQLite → Supabase free (Postgres + PostGIS + Auth) from Phase 6 | ₹0 |
| Cache / queue | In-process cache + GitHub Actions cron *(Redis cut — ADR-0003)* | ₹0 |
| Frontend | React + TS + Vite + MUI + react-leaflet + Recharts; free OSM/CARTO tiles | ₹0 |
| Reports | WeasyPrint server-side PDF | ₹0 |
| Hosting | Vercel Hobby + Render free + GitHub Actions | ₹0 |

Free-tier terms verified July 2026 — Gemini free tier is Flash-family only at ~10 req/min
and ~1,500 req/day; Render free sleeps after 15 min idle with 5 GB/mo bandwidth; Earth
Engine is free for students/noncommercial under a monthly compute-unit quota.

**Correction, 2026-07-27** (`conventions.md`'s dated-correction pattern, applied to this
non-ADR doc too — the decision to use Gemini free tier, ADR-0002, still stands; only the
supporting figure was wrong): live-verified during the Phase 4 agents build, the actual daily
cap hit was **20 requests/day**, not ~1,500 — Google's own `429` response named it explicitly:
`generate_content_free_tier_requests`, `GenerateRequestsPerDayPerProjectPerModel-FreeTier`,
`quotaValue: 20`, for the model `gemini-flash-latest` currently resolves to
(`gemini-3.6-flash`). Measured on a newly created AI Studio project — Google may grant higher
quotas to older or billing-verified projects, so this may not be universal, but it is real and
current for this project. Sharpens the case for caching (Rate-limit hygiene, PROGRESS.md):
20/day means a live demo cannot afford repeat identical calls, not just rapid-fire ones.

## 6. Phase roadmap

Each phase ends in something that runs and can be shown. Nothing is "integrated at the
end" — that is how student projects die.

| Phase | Weeks | Delivers | ✅ Exit criterion |
|---|---|---|---|
| **0 Foundations** | 1 | Repo, docs, accounts, env | Landsat image of Mumbai renders in a notebook |
| **1 Data pipeline** | 2–4 | Features for every grid cell | `features.parquet` + heat map notebook |
| **2 ML** | 5–7 | Trained model, SHAP, scenario fn | Greening scenario yields sensible ΔLST |
| **3 Backend** | 8–10 | FastAPI over the model | Everything demoable from `/docs` |
| **4 Agents** | 11–14 | Four agents + RAG + cron | Copilot answers a planning question with real numbers |
| **5 Dashboard** | 15–19 | React UI | Full end-to-end local demo |
| **6 Deploy** | 20–22 | Supabase + Vercel + Render | Public URLs work |
| **7 Polish** | 23–24+ | PDF reports, report, presentation prep | Report draft assembled from `docs/` |

Detail for phases 2+ is expanded into `PROGRESS.md` at each kickoff rather than
over-specified now — the shape of later phases depends on what phase 1's data reveals.

### Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Earth Engine approval delayed | Low | Registered day 1; Phase 0 is the only blocked work |
| Cloud cover ruins composites | Medium | Dry-season only + multi-year median compositing |
| Model R² disappointing | Medium | Baseline comparison framing — a weak-but-honest model with good SHAP still carries the project |
| Gemini rate limits during demo | Medium | Cache answers, backoff, canned demo script — no fallback provider (ADR-0011); warm the cache before a demo |
| Render cold start during a live demo | High | Wake the URL before presenting; local fallback ready |
| Scope creep (2nd city, mobile) | High | Parked-ideas list; nothing leaves it until Phase 7 |

## 7. Documentation system

Documentation is a per-task obligation, not a final-phase scramble. Rules live in
[conventions.md](conventions.md); the tree:

```
docs/
├── BLUEPRINT.md        this file — roadmap and scope
├── conventions.md      hard rules, Definition of Done, code + doc conventions
├── architecture.md     components, data flow, deployment (Mermaid, editable)
├── decisions/          ADRs — one per significant choice
├── data-dictionary.md  every dataset and feature: source, units, licence
├── ml-methodology.md   model design, validation, metrics, SHAP reading
├── api-reference.md    endpoint contracts and the why behind them
├── agents.md           agent roles, tools, prompts, guardrails
├── runbook.md          setup, run, deploy, rotate keys, troubleshoot
├── devlog.md           dated journal, one entry per session
├── references.md       papers and datasets → report bibliography
└── CHANGELOG.md        milestone history
```

By Phase 7 the final report is largely an assembly job: problem and scope from this file,
methodology from `ml-methodology.md` + `data-dictionary.md`, design from `architecture.md`
+ `decisions/`, results from notebooks, limitations from the honest notes kept throughout,
bibliography from `references.md`.

## 8. Working agreement

Session start: read `PROGRESS.md` → pick the top unchecked task → build → author verifies
the ✅ → docs updated → commit. Small commits, conventional prefixes, authored solely as
`DevGurav`. Phase kickoffs get a planning pass before code.
