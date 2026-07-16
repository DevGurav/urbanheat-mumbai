# Changelog

Milestone history. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
An entry lands when a **phase completes** (its ✅ exit criterion is verified) — session
detail belongs in [devlog.md](devlog.md).

---

## [Unreleased] — Phase 0: Foundations

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

### Pending for this phase
- Earth Engine noncommercial registration; Gemini API key
- Python 3.11 environment
- ✅ Exit criterion: Landsat LST image of Mumbai renders in a notebook

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
