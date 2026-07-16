# Devlog

Engineering journal — one entry per working session, newest first. Written for the future
author: what moved, what broke, what was decided, what to pick up next.

**Why keep this.** By Phase 7 the report needs a narrative — what was tried, what failed,
why the design is what it is. That narrative is impossible to reconstruct from a git log
six months later. Dead ends recorded here are worth as much as successes; a viva panel asks
"what didn't work?" and a real answer is a strong one.

**Entry template**

```markdown
## YYYY-MM-DD — Phase N — Title

**Done**
**Decided**
**Broke / learned**
**Next**
```

---

## 2026-07-17 — Phase 0 — Project scaffolding and documentation

**Done**
- Git repo connected to `github.com/DevGurav/urbanheat-mumbai`; local identity set.
- `.gitignore` extended (secrets, data artifacts, models, vector store); `.env.example`
  written with every variable the project will need through Phase 6.
- Root: `README.md`, `PROGRESS.md` (task board), `LICENSE` (MIT + data attributions).
- Full `docs/` tree: BLUEPRINT, conventions (hard rules + Definition of Done), architecture
  (Mermaid), data-dictionary, ml-methodology, agents, api-reference, runbook, references,
  CHANGELOG, this devlog.
- Six ADRs covering every load-bearing choice made so far.

**Decided**
- **Scope of the roadmap** — 8 phases over ~24 weeks, each ending in something runnable.
  No big-bang integration at the end.
- **ADR-0001 Earth Engine** over local raster processing. Deciding factor: where the compute
  happens. Terabytes of Landsat on a laptop with 10 GB free was never viable.
- **ADR-0002 Gemini Flash free tier**, Groq as fallback. Local Ollama rejected — no GPU
  means CPU inference too slow for an agent graph, and small-model tool calling is unreliable.
- **ADR-0003 Redis and WebSockets cut.** They solve multi-instance and push problems this
  system does not have; Render's free tier (one sleeping container, no worker) would make
  them inert. Staying in the report as production considerations with scaling triggers.
- **ADR-0004 Files first, Supabase from Phase 6.** The feature table is a regenerable build
  artifact, not database state. Supabase's idle-pause would also have been an outage risk
  during the ML phases.
- **ADR-0005 LST as target** — the most consequential decision. Air temperature has <10
  stations across the study area; a 20k-cell model trained on that would be interpolation
  wearing an ML costume. LST gives a measured label per cell. Cost: outputs are *surface*
  temperature, mid-morning, and must be labelled as such everywhere.
- **ADR-0006 Gradient-boosted trees.** At 20k×20 tabular, this is the right tool, not a
  compromise — and SHAP's exact tree explainer is what the whole recommendation layer
  stands on. Deep learning would be the wrong answer here, independent of hardware.

**Learned / noted**
- Free-tier terms verified as of today: Gemini free tier is Flash-only (~10 req/min,
  ~1,500/day) since Pro moved behind billing in May 2026; Render free sleeps at 15 min idle
  and dropped to 5 GB/mo bandwidth in April 2026; Earth Engine noncommercial runs on a
  monthly compute-unit quota. All three shape design, not just budget — recorded in the ADRs.
- Two risks written down early because they are the classic ways this kind of project
  produces a worthless-but-impressive result: spatial autocorrelation inflating R² under a
  random split, and the scenario engine extrapolating past the training envelope. Both have
  mitigations specified before any code exists (`ml-methodology.md` §2, §6).

**Next**
- Folder scaffold: `data-pipeline/`, `backend/`, `frontend/`, `notebooks/`, `data/`, `models/`.
- **Earth Engine noncommercial registration** — the only approval wait; blocks Phase 0's ✅.
- Gemini key → `.env`. Python 3.11 env + `earthengine-api`, `geemap`, `geopandas`.
- Then the Phase 0 exit criterion: a notebook rendering a Landsat LST image over Mumbai.
