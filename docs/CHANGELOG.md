# Changelog

Milestone history. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
An entry lands when a **phase completes** (its ✅ exit criterion is verified) — session
detail belongs in [devlog.md](devlog.md).

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
