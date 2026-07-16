# UrbanHeat AI — Mumbai

**AI-powered Urban Heat Island prediction, monitoring and mitigation recommendation system.**

Mumbai's built-up wards run measurably hotter than its green and coastal ones. This project
quantifies that gap from open satellite data, explains *why* each neighbourhood is hot,
simulates what would happen if you intervened (plant trees, coat roofs, add water bodies),
and exposes the whole thing through a map dashboard and a natural-language copilot that
urban planners can actually query.

> Final-year major project. Built entirely on free tiers and open data — no paid services.

---

## What it does

| Capability | How |
|---|---|
| **Measure** heat | Land Surface Temperature from Landsat 8/9 thermal bands, dry-season composites |
| **Explain** heat | XGBoost/LightGBM trained on vegetation, built-up density, albedo, land cover, population; SHAP attributes each cell's temperature to its causes |
| **Rank** priorities | Heat Vulnerability Index = heat exposure × population × lack of green cover, aggregated per BMC ward |
| **Simulate** interventions | Digital twin: change a cell's features → re-predict → ΔLST map with cost estimates |
| **Recommend** actions | Planning agent turns hotspots into ranked, costed mitigation plans grounded in published coefficients |
| **Monitor** conditions | Scheduled job watches forecasts and raises heatwave alerts |
| **Converse** | RAG copilot answers planner questions over city data + policy documents |

## Architecture

Four LangGraph agents (Planning, Digital Twin, Monitoring, Copilot) sit on top of an
ML prediction service, a GIS processing service and a scenario engine, all served by
FastAPI to a React dashboard.

Full component and data-flow diagrams: **[docs/architecture.md](docs/architecture.md)**

## Stack

**Data** Google Earth Engine (Landsat, Sentinel-2, ESA WorldCover, WorldPop, SRTM) · Open-Meteo · OpenStreetMap/OSMnx
**ML** scikit-learn · XGBoost · LightGBM · SHAP
**Backend** Python 3.11 · FastAPI · LangGraph · Gemini Flash · ChromaDB + sentence-transformers
**Frontend** React · TypeScript · Vite · MUI · react-leaflet · Recharts
**Infra** GitHub Actions · Vercel · Render · Supabase

Why each of these: **[docs/decisions/](docs/decisions/)**

## Status

**Phase 0 — Foundations.** See **[PROGRESS.md](PROGRESS.md)** for the live task board and
**[docs/BLUEPRINT.md](docs/BLUEPRINT.md)** for the full roadmap.

## Quickstart

Not yet runnable — the data pipeline lands in Phase 1. Setup instructions are being
maintained in **[docs/runbook.md](docs/runbook.md)** as each piece becomes real.

```bash
git clone https://github.com/DevGurav/urbanheat-mumbai.git
cd urbanheat-mumbai
cp .env.example .env    # then fill in GEE_PROJECT_ID and GEMINI_API_KEY
```

## Repository layout

```
data-pipeline/   Earth Engine + OSM + weather extraction → data/
data/            Feature tables, rasters (large files gitignored — regenerate via pipeline)
backend/         FastAPI: api/ ml/ agents/ rag/
frontend/        Vite + React + TypeScript dashboard
notebooks/       Exploration and ML experiments
docs/            Architecture, decisions, methodology, runbook, devlog
.github/         CI and scheduled monitoring workflow
```

## Documentation

| Doc | Contents |
|---|---|
| [BLUEPRINT.md](docs/BLUEPRINT.md) | Master roadmap: phases, exit criteria, scope |
| [conventions.md](docs/conventions.md) | Hard rules, Definition of Done, code conventions |
| [architecture.md](docs/architecture.md) | Components, data flow, deployment topology |
| [decisions/](docs/decisions/) | Architecture decision records — why each choice |
| [data-dictionary.md](docs/data-dictionary.md) | Every dataset and feature: source, units, licence |
| [ml-methodology.md](docs/ml-methodology.md) | Model design, validation strategy, metrics |
| [agents.md](docs/agents.md) | Agent roles, tools, prompts, guardrails |
| [api-reference.md](docs/api-reference.md) | Endpoint contracts |
| [runbook.md](docs/runbook.md) | Setup, run, deploy, troubleshoot |
| [devlog.md](docs/devlog.md) | Session-by-session engineering journal |
| [references.md](docs/references.md) | Papers and datasets cited |

## Licence & data attribution

Code: MIT (see `LICENSE`). Data sources retain their own licences — Landsat/SRTM are
public domain (USGS/NASA), Sentinel-2 and ESA WorldCover are CC BY 4.0, WorldPop is
CC BY 4.0, OpenStreetMap is ODbL. Attribution details in
[docs/data-dictionary.md](docs/data-dictionary.md).

---

**Author:** Devendra Gurav ([@DevGurav](https://github.com/DevGurav))
