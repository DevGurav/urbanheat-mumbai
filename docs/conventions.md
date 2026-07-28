# Conventions

How this project is built. Read alongside [BLUEPRINT.md](BLUEPRINT.md) (roadmap) and
[../PROGRESS.md](../PROGRESS.md) (current tasks).

---

## Hard rules

**Zero paid services.** Every tool, API and host must be free tier or open source. If a
step would incur charges, stop and find a free alternative. Rationale for each pick lives
in [decisions/](decisions/).

**Secrets stay out of git.** All keys live in `.env` (gitignored), documented in
`.env.example`. Never hardcode a key. Every LLM call goes through the backend — the
frontend never holds a provider key.

**Data discipline.** Heavy raster math stays in Earth Engine's cloud (ADR-0001). The repo
stores only grid-level tables and small derived rasters. Anything large is gitignored and
**must** be regenerable by re-running `data-pipeline/` — that contract is what makes
excluding it safe (ADR-0004).

**Numbers come from tools, never from prose.** Any temperature, cost or ranking shown to a
user must trace back to a dataset, the model, or a cited source. A plausible-looking
invented number is the worst defect this system can ship (see [agents.md](agents.md) §1).

---

## Definition of Done

A task is done when:

1. The code runs.
2. The phase exit criterion (✅ in `PROGRESS.md`) is **verified**, not assumed.
3. Docs are updated — devlog always; ADR / data-dictionary / api-reference when applicable.
4. It is committed.

---

## Git

Small, frequent commits. Conventional prefixes:

```
feat:   new capability          fix:   bug fix
data:   pipeline/dataset change docs:  documentation
chore:  tooling, deps, config   test:  tests
```

Author: `DevGurav <dev.gurav011@gmail.com>`. No co-author trailers.

---

## Documentation rules

Documentation is part of the work, not a phase at the end. By Phase 7 the final report
should be largely an assembly job — that only holds if these are kept up as work happens.

| Trigger | Required update |
|---|---|
| Significant technical decision | New ADR in [decisions/](decisions/) |
| Any working session | Dated entry in [devlog.md](devlog.md) |
| New dataset or feature column | Row in [data-dictionary.md](data-dictionary.md), same day |
| Endpoint added or changed | [api-reference.md](api-reference.md) |
| Agent prompt or tool changed | [agents.md](agents.md) |
| Phase completed | [CHANGELOG.md](CHANGELOG.md) + check [architecture.md](architecture.md) still matches reality |
| Paper or dataset consulted | [references.md](references.md) |

ADRs are **immutable** once committed. To reverse a decision, write a new ADR that
supersedes the old one and mark the old one `Superseded by ADR-XXXX`. The rejected options
are the valuable part — they are what a technical reviewer asks about.

---

## Code conventions

**Python** — `ruff` for lint + format, line length 100. Type hints on public functions.
Pydantic models at every API boundary. Config via `pydantic-settings` reading `.env` — no
bare `os.environ` scattered through modules. Notebooks are for exploration; anything reused
gets promoted into a module.

**TypeScript** — strict mode. No `any` without a comment justifying it. API response types
mirror the backend Pydantic schemas.

**Geospatial** — EPSG:4326 for storage and API responses; project to EPSG:32643 (UTM 43N)
for area and distance maths. Every grid cell carries a stable `cell_id` — **never reindex
it**; it is the join key across the pipeline, the model and the API.

**Comments** — explain constraints and non-obvious *why*, not *what*.

**Terminology** — outputs are **surface** temperature, never "temperature" unqualified
(ADR-0005). This applies to UI copy, API fields, chart axes and the report.

---

## Gotchas already known

- **Monsoon clouds.** Never composite optical or thermal imagery over Mumbai for Jun–Sep.
  Dry season (Mar–May) only.
- **Earth Engine quota.** Export aggregates, not rasters. Never call `getInfo()` in a
  per-cell loop — it will burn the monthly compute quota fast (ADR-0001).
- **Spatial autocorrelation.** A random train/test split will report an inflated R².
  Blocked cross-validation is mandatory ([ml-methodology.md](ml-methodology.md) §2).
- **LLM rate limits.** ~10 req/min on the free tier — cache, back off, fall back
  (ADR-0002).
- **Render cold start.** Free tier sleeps after 15 min idle, ~1 min to wake. Wake it before
  any demo ([runbook.md](runbook.md) §5).
