# PROGRESS — UrbanHeat AI

Live task board. Newest phases get expanded into detailed tasks at their kickoff.

**Legend** `[ ]` todo · `[~]` in progress · `[x]` done · ✅ phase exit criterion
**Current phase:** 7 — Polish & report *(Phase 6 complete — public URLs live)*
**Last updated:** 2026-07-29

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

**Goal:** a trained, explained LST model; a Heat Vulnerability Index; a scenario engine that
turns interventions into a ΔLST map. Everything runs locally on `features.parquet`.

**Settled at kickoff, 2026-07-26 (ADR-0008)**
Target `lst_mean` · train/evaluate on `land_fraction ≥ 0.5`, predict on all land cells ·
**ward-grouped k-fold** spatial CV (GroupKFold on `ward_code`) · features exclude absolute
location (`ward_code`, `centroid_lat/lon`) and the leakage columns (`lst_p90`,
`lst_obs_count`, `wc_pixels`).

### Data prep & validation harness

- [X] `ml/dataset.py` — X, y, ward groups from `features.parquet`; training filter + leakage/
  location exclusions (30 features; dropped `population` as collinear, kept `land_fraction`)
- [X] `ml/cv.py` — ward-grouped `GroupKFold` splitter + spatial/random scorer (R², RMSE, MAE)
- [X] Random-vs-spatial gap reported — **tiny (~0.047)**, evidencing that excluding location
  (ADR-0008) stopped the model memorising the map

### Models

- [X] Baseline — mean floor + ridge (the honest floor: mean is negative under spatial CV)
- [X] Random forest → XGBoost → LightGBM; light defaults only
- [X] Model comparison table → `docs/ml-methodology.md` §3; **XGBoost saved** (spatial R² 0.893,
  RMSE 1.10 °C) → `models/model.joblib` + `model_meta.json`

### Explainability

- [X] SHAP TreeExplainer — global importance + per-cell attribution → `models/shap_values.parquet`
  *(top: ndbi 1.41, albedo 0.51, pop_density 0.37, built 0.36)*
- [X] **Physics gate** — enforced on 8 load-bearing drivers (all pass); `albedo` warm = the
  expected confound (ADR-0008); collinear features reported as SHAP credit-sharing, not gated

### Heat Vulnerability Index

- [X] `hvi` — 0.4/0.4/0.2 blend of heat / pop_density / lack-of-green → `data/processed/hvi.parquet`
  (own file, not a model feature — derived from the target). Weight-sensitivity **passes**:
  top-10 wards stable 9–10/10, Spearman ρ ≥ 0.98
- [X] `hotspot_rank` + ward hotspot ranking (top: B, L, C, H/E, F/S, K/E, G/N, E — dense & hot)

### Scenario engine v1

- [X] `simulate(feature_deltas) → ΔLST`, clamped to the training envelope (no extrapolation)
- [X] Intervention → feature-delta map with **cited** coefficients (Li et al. 2014, Grover &
  Singh 2015 in `references.md`); **cool-roof uses the cited albedo coefficient, not the
  model's** (albedo confound, ADR-0008). Greening floored at ΔLST ≤ 0 (off-manifold warming)
- [X] ✅ **Saved model + metrics; a greening scenario produces a sensible ΔLST map**
  — model saved (XGBoost, spatial R² 0.893); greening cools 7,410 cells (mean −0.65, best
  −4.88 °C) in the hot grey wards. **Awaiting the author's check of the ΔLST map to tick.**

---

## Phase 3 — Backend API · Weeks 8–10

**Goal:** a FastAPI backend over the trained model, HVI and scenario engine — everything
demoable from Swagger `/docs`. No DB (ADR-0004: files in memory); no Redis (ADR-0003:
in-process cache). Contracts in `api-reference.md`.

**Approach.** A `backend/` package loads the processed artifacts once at startup
(`features.parquet`, `hvi.parquet`, `wards.geojson`, `models/model.joblib`,
`models/shap_values.parquet` — a few MB, ADR-0004) into an in-memory store. Routers read that
store; pydantic schemas type every response and carry the `measurement` marker (ADR-0005).

### Skeleton

- [X] `backend/` package: FastAPI app, `pydantic-settings`, CORS from `CORS_ORIGINS`, gzip, logging
- [X] Startup store (`store.py`): load model + tables once; `GET /health` → model/data version + uptime
- [X] `schemas.py` scaffold + the `measurement: land_surface_temperature` marker (applied per endpoint)

### Data-serving endpoints

- [X] `GET /city/grid` — choropleth GeoJSON (`layer=lst|ndvi|hvi|built`), geometry simplified + gzipped
- [X] `GET /hotspots` — ranked wards/cells by `hvi|lst`, each with its top SHAP driver
- [X] `GET /explain/{cell_id}` — per-cell SHAP attribution (the product's "why")
- [X] `GET /weather` — Open-Meteo passthrough, TTL-cached

### Model / scenario endpoints

- [X] `GET /predict` — model LST prediction for a cell (transparency: predicted vs. observed)
- [X] `POST /scenario` — wraps `ml/scenario.py`: ΔLST + summary + the `clamped` disclosure
  (no cost field — no cited cost figure exists yet, see api-reference.md)
- [X] `GET /trends` — **stubbed**: `{available: false, note: ...}`; real slopes need `lst_trend` (deferred)

### Performance & exit

- [X] GZip middleware + geometry simplification for `/city/grid`; in-process TTL cache
- [X] Keep `api-reference.md` in sync as endpoints land
- [X] ✅ **Everything demoable from Swagger `/docs` locally**

---

## Phase 4 — Agentic core · Weeks 11–14

**Goal:** four LangGraph agents wrapping the Phase 3 services, a RAG-backed Copilot, and a
daily monitoring cron — reachable through one new endpoint, `POST /agent/chat`. Contracts and
guardrails in `agents.md`.

**Settled at kickoff, 2026-07-27 (ADR-0009)**
Tools wired **in-process** (`backend.store` / `data_pipeline.ml.*` imports, not HTTP loopback)
· agent numbering canonicalized **1 Copilot · 2 Planning · 3 Digital Twin · 4 Monitoring**
(fixed a diagram/diagram vs. prose/PROGRESS inconsistency found across `agents.md` and
`architecture.md`) · RAG corpus is a **3-document MVP** (MCAP, NDMA guidelines, IMD criteria) —
WHO/IPCC/other-cities' plans deferred · Agent 2 ranks by **ΔLST × population only**, no cost
(`estimate_cost`/`interventions.yaml` deferred — no cited cost-per-area figure exists yet)

### Dependencies & environment

- [X] Add `langchain`, `langgraph`, `chromadb`, `sentence-transformers`, `langchain-groq` to
  `pyproject.toml` *(plus `langchain-google-genai` — needed for the primary Gemini provider,
  not just the Groq fallback; not enumerated at kickoff but implied by ADR-0002)*
- [X] Confirm `GEMINI_API_KEY` / `GROQ_API_KEY` / `CHROMA_DIR` flow through `pydantic-settings`
  — added to `data_pipeline/config.py`'s `Settings` with empty-string/default fallbacks so a
  fresh clone with no LLM key still runs (`docs/conventions.md`); `chroma_dir` resolved
  against the repo root like `data_dir`/`model_dir`

### Shared toolbelt

- [X] `get_hotspots`, `get_cell_stats`, `explain_cell`, `explain_ward`, `simulate_scenario`,
  `get_weather`, `get_trend` — in-process LangChain `StructuredTool`s (`backend/agents/tools.py`)
  over `backend/services.py` (ADR-0009). Router logic for the five existing endpoints moved
  into `services.py` so the HTTP routes and the tools call the same functions, not two
  implementations; `get_cell_stats` and `explain_ward` are new logic, not wraps of an existing
  endpoint. Pydantic-validated args per tool; every result carries `model_version`/provenance,
  and a domain error (unknown cell/ward) comes back as a labelled `{error, error_code}` dict
  instead of raising, so a bad lookup reads as "couldn't find that", not a crash
  (`agents.md` §1). `search_knowledge` stays with the **RAG knowledge base** group below — it
  needs the Chroma index that group builds, so it can't be wired before that
- [X] Unit tests per tool against the real fixtures — `tests/test_agent_tools.py`, 12 tests

### RAG knowledge base

- [X] Collect the 3 MVP documents → `data/knowledge_base/` (gitignored); log as read in
  `references.md` §4 — MCAP Summary for Policymakers and the IMD FAQ on Heat Wave both had
  real text layers (extracted with `pypdf`, no OCR needed); NDMA's own detailed guideline PDF
  turned out to be a 62-page scan with none, so its official heat-wave hazard page substitutes
  for it — logged as a limitation in `references.md`, not a silent swap. Real IMD criteria
  captured with primary-source precision: 40 °C (plains) / 30 °C (hilly) base threshold,
  departure bands, coastal-station rule, 2-station/2-day declaration rule
- [X] `backend/rag/ingest.py` — chunk (~800 words / 100 overlap, a word-count proxy for tokens)
  and embed (`sentence-transformers/all-MiniLM-L6-v2`, CPU) into a persisted Chroma index at
  `CHROMA_DIR`. 28 chunks indexed from the 3 sources; `backend/rag/retrieve.py`'s `Retriever`
  does the query side. `pypdf` added to `pyproject.toml` for future document collection too,
  not just this run
- [X] `search_knowledge` tool — top-k 4, passage + source + page (`backend/agents/tools.py`);
  `build_toolbelt` takes an optional `retriever` so a fresh clone without a built index still
  gets the other 7 tools rather than failing

### Agents

- [X] Agent 1 — Urban AI Copilot (RAG + data tools; guardrails in `agents.md` §4) —
  `backend/agents/copilot.py`, every toolbelt tool except `simulate_scenario`
- [X] Agent 2 — Planning Decision (hotspots → SHAP → simulate → rank by ΔLST × population;
  no cost field per kickoff scope, `agents.md` §5) — `backend/agents/planning.py`
- [X] Agent 3 — Digital Twin (NL → structured scenario → `simulate_scenario` → narration,
  `agents.md` §6) — `backend/agents/digital_twin.py`
- [X] Agent 4 — Monitoring (rule-based IMD thresholds in code, not LLM-judged; LLM drafts
  alert wording only, `agents.md` §7) — `backend/agents/monitoring.py`. Not a tool-calling
  loop like the other three: absolute-temperature-only trigger (37/45/47 °C, real IMD FAQ
  numbers), because IMD's full coastal criteria need a "departure from normal" baseline this
  project doesn't have as a real climatological normal (ADR-0010)
- [X] `backend/agents/llm.py` (Gemini binding, no retry/fallback yet — that's Rate-limit
  hygiene's job), `prompts.py` (the 4 system prompts), `result.py` (`run_agent`: flattens a
  compiled graph's message trace into text + `tool_calls`, bounded to `MAX_TOOL_CALLS=4` via
  `recursion_limit`, catches a runaway loop instead of hanging)
- [X] `tests/test_agents.py` — 16 tests against the real tool-calling loop (real tools, real
  store, a small local fake chat model in place of Gemini — verifies tool wiring per agent,
  `run_agent`'s extraction, error-as-labelled-result (not a crash), and the recursion-limit
  catch). Monitoring's `_severity()` thresholds tested directly (pure logic), its LLM-drafted
  wording tested with a mocked call
- [X] **Live LLM verification — resolved 2026-07-27.** A key from a genuinely different
  Google account (not a new key on the same denied project) worked immediately, confirming
  the block really was project-level (`runbook.md`, `devlog.md`). Live-verified all four
  agents plus the supervisor: Copilot correctly chained `get_hotspots` → `explain_ward` for a
  cited, well-formatted answer; Planning chained `explain_ward` → `get_hotspots` →
  `simulate_scenario` ×2 (both interventions) and ranked them with no cost mentioned (ADR-0009
  scope holding under a real model, not just the system prompt); Digital Twin correctly
  refused to apply an unsupported coverage fraction to greening and phrased its result as
  analogy, not causation; Monitoring's real forecast check didn't trigger (expected, ADR-0010)
  and its wording-drafting path produced a properly caveated advisory when forced; the
  supervisor routed all three test messages to their correct agent. **Two real bugs found live
  that 94 mock-tested cases had missed**, both the same shape: `AIMessage.content` from real
  Gemini is a list of content blocks, not a plain string (carries a response `signature`) —
  `str(response.content)` silently produced garbage. Fixed in `result.py`'s final-answer
  extraction and `monitoring.py`'s summary draft using `.text` (a `BaseMessage` accessor that
  normalizes either shape) instead of `.content`. The same bug in `supervisor.py`'s `route()`
  was the more serious one: it would have silently routed every message to the `copilot`
  fallback, since the stringified block list never equals `"planning"`/`"digital_twin"` —
  fixed identically. Also hit and correctly handled a real `429` quota error (confirms the
  `agent_upstream_unavailable` path works, not just the happy path) — and that error revealed
  the real free-tier daily quota is 20 req/day, not the ~1,500 `BLUEPRINT.md` documented;
  corrected there with a dated note

### Orchestration

- [X] Supervisor — single classification hop routes to one of three agents (`agents.md` §2);
  Monitoring is never chat-routed, only cron-triggered (§7). `backend/agents/supervisor.py`:
  a plain one-word classification, parsed and validated in Python (not `with_structured_output`
  — its default tool-calling flow adds a layer this project doesn't need), falling back to
  Copilot on an unparseable reply rather than guessing intent. One `Supervisor` built once at
  startup, sharing one LLM binding across the router and all three agents' own tool-call loops
  (bounded to `MAX_TOOL_CALLS=4` each, already built in the Agents task group)
- [X] `POST /agent/chat` — narrative + `tool_calls` made (transparency) + optional GeoJSON
  layer (`api-reference.md`, `backend/routers/agent.py`). The layer comes from
  `build_agent_layer()`: if the dispatched agent called `simulate_scenario`, build a
  `/city/grid`-shaped GeoJSON scoped to just those cells; otherwise `null`, not invented.
  `app.state.supervisor` is built once at startup and stays `None` — a clean 503, not a crash
  — if the RAG index isn't built or `GEMINI_API_KEY` is unset entirely; a *present but broken*
  key (this repo's current state, `403 PERMISSION_DENIED`) surfaces as a 503 at request time
  instead, since Supervisor construction alone doesn't spend a call to check
- [X] `tests/test_orchestration.py` — 13 tests: routing/fallback (parametrized), dispatch +
  tool-call surfacing, `build_agent_layer` (real scenario call, non-scenario call, errored
  call, no calls), and the endpoint's three response paths (200, both 503s) via `TestClient`
  with a mocked supervisor. Moved `store`/`retriever` fixtures to `conftest.py`, session-scoped
  — they were duplicated function-scoped in three test files and had started measurably
  slowing the suite (repeated store/embedding-model reloads)

### Rate-limit hygiene

**Settled 2026-07-27 (ADR-0011):** dropped the Groq fallback — one credential to manage, not
two; the cache below covers the practical case (repeat demo questions) it mainly protected
against. Real number behind all of this: **20 req/day**, not the ~1,500 `BLUEPRINT.md`
originally assumed — measured live from a real `429` during the Phase 4 agents build.

- [X] Response cache keyed on (question + `data_version`) — `Supervisor`'s own `TTLCache`
  (`backend/agents/supervisor.py`), 24h TTL, exact-string-match key (no fuzzy matching — a
  rephrased question at demo time is a genuine miss, `runbook.md` §5). A failed call is never
  cached (`TTLCache.get_or_set` only stores after `compute()` returns, so an exception
  propagates before the write)
- [X] Exponential backoff on 429 — already built into `ChatGoogleGenerativeAI`'s own client
  (live-observed: 1s/2s/4s/8s retries before raising); made the retry count explicit
  (`max_retries=3` in `backend/agents/llm.py`) rather than the library's default of 6, so a
  doomed request (daily quota actually exhausted) doesn't make `/agent/chat` wait 30+ seconds
  before the honest 503. ~~Groq fallback~~ dropped (ADR-0011)
- [X] Runbook step: warm the cache with the scripted demo questions before a live demo —
  `runbook.md` §5, rewritten with the real 20/day number and the exact-match caveat
- [X] Tests: `tests/test_orchestration.py` — cache hit on an identical question (no second LLM
  call — a scripted-response-exhaustion `IndexError` would fail the test if it weren't
  cached), cache miss on a reworded question, a failed call not poisoning the cache,
  `get_llm()`'s explicit `max_retries`

### Monitoring cron

- [X] `.github/workflows/monitoring.yml` — daily trigger, `30 0 * * *` UTC (06:00 IST).
  Doesn't rebuild the pipeline or run the check itself — calls the deployed backend's
  `POST /monitoring/check` (matches `architecture.md` §6's original design: GA → trigger →
  Render). **Inert until Phase 6** sets a `BACKEND_URL` secret — exits cleanly (not a failure)
  when it's unset, since there's no deployed backend yet for it to call
- [X] `POST /monitoring/check` + `GET /alerts` (`backend/routers/monitoring.py`,
  `backend/routers/alerts.py`) — the server-side trigger point and the read-back feed
  `api-reference.md` already sketched. Independent of `app.state.supervisor`: Monitoring's
  deterministic trigger doesn't need the RAG index or the chat agents to be configured
- [X] Alert dedupe (one per event, not per run) + file persistence (Phase 4; Supabase from
  Phase 6) — `backend/agents/alerts.py`. State (`alerts_state.json`) tracks yesterday's
  severity; a fresh trigger or a severity *escalation* gets logged (`alerts.jsonl`), continuing
  at the same or a lower severity doesn't. `monitoring.py`'s wording draft now also falls back
  to a fixed template if the LLM is unavailable — the trigger is real and deterministic
  regardless of whether an LLM is around to phrase it (a gap the live-verification session
  exposed was worth closing, given how much this project's LLM credential has already broken)
- [X] Tests: `tests/test_monitoring_cron.py` — 10 tests, the full dedupe matrix (new event,
  continuing, escalation, de-escalation, a fresh event after a gap) plus both endpoints via
  `TestClient`, all against `tmp_path` so the real `data/processed/alerts*` files are never
  touched by the suite

### Exit

- [X] ✅ **Copilot answers a real planning question with real model numbers**

---

## Phase 5 — React dashboard · Weeks 15–19

**Goal:** a single-page dashboard over the ten endpoints Phases 3–4 already serve — heat map,
analytics, scenario simulator, Copilot chat, alerts feed. Everything Phase 4 built stays
backend-only otherwise; this phase is purely the UI over it.

**Settled at kickoff, 2026-07-27** (implementation patterns within `BLUEPRINT.md`'s already-
locked stack — React + TS + Vite + MUI + react-leaflet + Recharts — not new architectural
decisions, so no new ADR):
**TanStack Query** for fetching/caching (matters more than usual here — `/agent/chat` is slow
and quota-limited at 20 req/day, and a caching layer prevents accidental refetch spam the
backend's own cache already assumes won't happen) · **hand-written TypeScript types** mirroring
`backend/schemas.py` (`conventions.md`'s literal wording; no OpenAPI codegen step) ·
**single page with a section switcher**, no router (five sections, no need for shareable
per-section URLs) · **Definition of Done is manual/visual verification** in a running dev
server, not an automated component test suite (the standing UI-work instruction, not a new
Vitest/RTL suite for a solo dashboard).

### Scaffold & plumbing

- [X] `npm create vite@latest` (React + TS template) in `frontend/`; strict `tsconfig`
  (`conventions.md`: no `any` without a comment justifying it) — **the scaffold didn't set
  `strict: true` by default**, added explicitly to `tsconfig.app.json`, verified by `npx tsc -b`
  actually failing before the fix. MUI theme (`createTheme`, heat-red primary, not MUI's
  default blue) in `main.tsx`. Removed the scaffold's marketing-page boilerplate
  (`App.css`, hero/react/vite images, the fixed-1126px-column `index.css`) — it would have
  visually conflicted with a full-height app layout
- [X] API client (`src/api/client.ts`) — thin `fetch` wrapper reading `VITE_API_BASE_URL`;
  one typed function per endpoint; types (`src/api/types.ts`) mirroring `backend/schemas.py`.
  **Caught before it shipped:** an early draft invented two client functions
  (`cellStats`/`explainWard`) for endpoints that don't exist — `get_cell_stats` and
  `explain_ward` are agent-toolbelt-only (`backend/agents/tools.py`), never exposed as REST
  routes. Cross-checked against `grep "@router\." backend/routers/*.py`'s actual 11 routes
  before trusting the client; removed both
- [X] TanStack Query setup — `QueryClientProvider` (`refetchOnWindowFocus: false` — the real
  20 req/day quota makes aggressive refetch defaults a real cost, not just noise), one hook
  per client-facing endpoint (`src/api/hooks.ts`). No `useMonitoringCheck` — that endpoint is
  cron-only, never called from the browser
- [X] App shell — MUI `AppBar` + `Tabs` switching between the five sections, all state in one
  `App` component (no router, per kickoff decision); each section is a `Placeholder` until
  its own task group lands
- [X] Verified live in a browser (Playwright, headless Chromium — no `chromium-cli` available
  on this Windows environment, installed `playwright` locally with `--no-save` for the check
  and removed it after): AppBar renders, all 5 tabs switch content correctly, zero console
  errors. Screenshots confirmed MUI theming applied, not unstyled HTML

### Heat map

- [X] `react-leaflet` map (`src/sections/HeatMap.tsx`), free CARTO Positron basemap tiles (no
  tile cost, `BLUEPRINT.md` §5)
- [X] `/city/grid` GeoJSON layer, layer toggle (`lst`/`ndvi`/`hvi`/`built`); **canvas
  renderer** (`preferCanvas`), not SVG — ~12k polygons per layer. Colored with the dataviz
  skill's validated sequential-blue ramp (`src/viz/color.ts`, copied verbatim from
  `references/palette.md` — no eyeballed hex values), one shared ramp across all four layers
  since only one renders at a time; a labeled gradient legend (`SequentialLegend.tsx`) so the
  map is never color-alone
- [X] Click a cell → `/explain/{cell_id}` side panel (SHAP drivers, the product's "why") — the
  driver list uses the dataviz skill's diverging blue↔red pair for warming/cooling direction,
  the one place on this map where the choice is polarity, not magnitude
- [X] Verified live with the real backend running (not just `tsc`/lint): real ~12k-cell grid
  rendered, legend showed a real 29.8–50.6 °C LST range; clicking a canvas-rendered cell
  (no per-shape DOM in canvas mode, confirmed by dropping the `.leaflet-interactive` selector
  approach and clicking screen coordinates instead) opened the drawer with real SHAP drivers
  for a real cell (Ward P/S, 41.5 °C, +1.6 °C vs city mean); switching to NDVI updated data
  and legend range correctly (−0.2 to 0.7); zero console errors throughout. **Caught and
  fixed live, not in review:** the layer-toggle buttons initially overlapped Leaflet's default
  zoom control (both top-left) — found in the first screenshot, fixed by offsetting the toggle
  group, re-verified in a second screenshot

### Analytics

- [X] `/hotspots` ranking (ward/cell, `hvi`/`lst` toggles) — horizontal Recharts bar chart +
  MUI table (`src/sections/Analytics.tsx`). One series (rank by value), so one sequential-blue
  color per the dataviz skill's color-formula — no legend needed, the axis labels are the
  identity. Added `CATEGORICAL` to `src/viz/color.ts` (the palette's first 3 slots — this
  project never needs more than 2 series at once) for the weather chart below
- [X] `/weather` forecast widget — a 7-day max/min line chart, 2 series, categorical colors
  (orange=max, blue=min — a fixed, intuitive assignment, not re-ranked per render)
- [X] `/trends` — an honest "not yet available" state, matching the backend's own stub
  (`{available: false}`) rather than hiding or faking the section
- [X] Verified live with the real backend: HVI ward ranking (B, L, C, H/E, F/S...) matched
  Phase 2's own recorded ranking exactly (`data-dictionary.md`) — a real cross-check, not
  just "a chart rendered." Toggling to LST/cell re-fetched and re-rendered correctly. Zero
  console errors. **Caught and fixed live:** the ranking chart's Y-axis had a fixed
  `width={60}` sized for ward codes ("B", "H/E") — cell IDs are 11-digit numbers and were
  silently truncated ("549001410" instead of "10549001410") until the toggle-to-cell
  screenshot caught it; width is now conditional on `unit`

### Scenario simulator

- [X] Ward + intervention (`greening`/`cool_roof`) + coverage form → `POST /scenario`
  (`src/sections/Scenario.tsx`). Ward list reuses `useHotspots(24, "hvi", "ward")` rather than
  a new endpoint — all 24 wards, not a ranking, just enumerated off an existing hook. Coverage
  slider disabled with an explanatory line when `greening` is selected, since the backend
  ignores it there
- [X] ΔLST summary + per-cell map overlay of the affected cells. `/scenario` returns
  `cell_id`/`dlst` only, no geometry — joined client-side against `/city/grid`'s already-typed
  features by `cell_id` (the same join `backend/agents/supervisor.py`'s `build_agent_layer`
  does server-side for `/agent/chat`, done here in the browser instead). Colored sequential
  (dlst is always ≤ 0 — a magnitude of cooling, not a polarity), scale bounds `[0, best_dlst]`
- [X] `clamped`/`clamped_cells` surfaced prominently, not buried — a warning-severity `Alert`
  directly under the summary line, not a footnote (ADR-0006)
- [X] Verified live with the real backend: Ward L greening → 391 cells, mean −1.03 °C, best
  −3.59 °C; cool-roof at 100% → mean −2.38 °C, best −3.40 °C — **both numbers match exactly**
  what the live-verified Planning agent produced for the same ward earlier this phase
  (devlog.md), a real cross-check between two independent call paths (UI → `/scenario` HTTP
  vs. agent → `simulate_scenario` tool) hitting the same backend logic. Coverage slider
  correctly disabled/enabled per intervention. Zero console errors. **Honest gap, not
  silently skipped:** queried `/scenario` directly for all 24 real wards — none produce
  `clamped_cells > 0` for greening, and cool-roof never clamps by construction (a cited
  formula, not a model call) — so the clamped `Alert`'s render path is verified by code
  review only, not by an actual live trigger; the dataset may simply never exercise it

### Copilot chat

- [X] Chat UI → `POST /agent/chat`; multi-second "thinking" state (LLM-bound, not a bug) —
  `src/sections/Chat.tsx`. Local turn history only (user/assistant/error bubbles) — the
  backend has no conversation memory (`session_id` is accepted but unused), so there is
  nothing further to keep in sync
- [X] Tool-call transparency — a collapsed-by-default "Show N tool calls" disclosure per
  reply, expanding to real tool name + args + a truncated JSON result per call
  (`api-reference.md`'s "the panel will ask")
- [X] Honest handling of both 503s (`agent_layer_unavailable`, `agent_upstream_unavailable`)
  with distinct messages, and a persistent info banner naming the real measured 20 req/day
  cap (`BLUEPRINT.md`, ADR-0011) — this is the one section most likely to hit a real rate
  limit during a live demo
- [X] Render the optional GeoJSON `layer` on the map when a response includes one — reuses
  the sequential-cooling color scale from `Scenario.tsx`
- [X] **Added `react-markdown`, not in the original task list** — found live: every real
  Copilot/Planning response uses markdown heavily (headers, bold, lists), and rendering it as
  literal `**`/`###` text was a real, visible readability bug affecting every reply, not a
  cosmetic nice-to-have. Small, standard dependency, scoped to this one rendering concern
- [X] Verified live with **one real LLM call, deliberately** ("Which ward in Mumbai is
  hottest?" → Copilot → `get_hotspots` + `explain_ward` → Ward L, 43.18 °C, matching every
  earlier verification of this same fact this phase). Re-sending the identical question
  after adding `react-markdown` was a cache hit (near-instant, no new tool calls) —
  confirms `Supervisor`'s `(question, data_version)` cache works correctly, as a bonus,
  not just the rendering fix. Zero console errors

### Alerts feed

- [X] `GET /alerts` polling list (`src/sections/Alerts.tsx`) — `refetchInterval: 5 * 60_000`
  on the query (ADR-0003, polled not pushed); the underlying feed is daily-refreshed, so a
  5-minute client poll is well within budget without hammering the backend
- [X] Severity-coded — the dataviz skill's **Status** color job (advisory/heat_wave/
  severe_heat_wave → warning/serious/critical from `references/palette.md`), always icon +
  label per the skill's rule, never color alone. Added `STATUS` to `src/viz/color.ts`
- [X] Honest empty state — "no active alerts" reads as calm (a green outlined `Alert`), not
  broken, with the ADR-0010 context for *why* that's the expected common case
- [X] Verified live: the real empty state (genuinely no alerts have ever fired — confirmed
  again, `read_alerts()` returns `[]`). For the populated state, wrote 3 realistic entries
  (one per severity, matching `backend/agents/alerts.py`'s exact JSONL shape) directly to
  the gitignored `data/processed/alerts.jsonl`, screenshotted all three severity colors
  rendering correctly with escalating color + newest-first order, then **deleted the file
  again** — the real system has never triggered a real alert, and leaving fake data in a
  gitignored-but-local file would misrepresent that. Zero console errors throughout

### Exit

- [X] ✅ **Full end-to-end local demo** — author-verified live in the browser, not assumed

---

## Phase 6 — Persistence, auth, deployment · Weeks 20–22

**Goal:** the gap between "runs on my machine" and public URLs — Supabase for the two
genuinely transactional tables, Auth on the one write endpoint that needs it, and the
backend/frontend/cron actually deployed and talking to each other.

**Settled at kickoff, 2026-07-28**
**Saved scenarios store config only** (`ward_code`, `intervention`, `coverage`,
`user_id`, `saved_at`) — loading one re-calls the real `/scenario` endpoint, so the result is
always freshly computed, never a stale snapshot · **Auth is magic-link / email OTP**
(Supabase's built-in passwordless flow — no OAuth app to register, fits the non-technical
personas `architecture.md` §1 actually names) · **Alerts stay file-based, not Supabase**
(ADR-0012, a partial revision of ADR-0004 — alerts turned out to be public/regenerable, not
transactional; users and saved scenarios move to Supabase exactly as ADR-0004 already
decided)

### Supabase schema & RLS

- [X] Supabase project (free tier) — `SUPABASE_URL`/`SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_KEY`
  → `.env` (author's own account, `runbook.md` §1.4). The URL the dashboard's own copy
  button produced was actually a `sb_publishable_...` key, not a URL — caught live (the
  frontend's Supabase client threw `Invalid supabaseUrl` on first real page load) and
  corrected by decoding the `ref` claim out of the anon/service JWTs already in `.env`
  instead of asking for a re-paste
- [X] `saved_scenarios` table: `id`, `user_id` (FK → `auth.users`), `ward_code`,
  `intervention`, `coverage`, `saved_at`. No custom `profiles` table — Supabase Auth's own
  `auth.users` is enough, nothing in this app needs extra profile fields yet —
  `supabase/schema.sql`, not yet run against the live project (author action still pending)
- [X] RLS: a user can only select/insert/delete their own `saved_scenarios` rows
  (`user_id = auth.uid()`) — the one place this project holds per-user data —
  `supabase/schema.sql`, not yet run against the live project (author action still pending)

### Auth

- [X] Magic-link sign-in flow in the frontend (email → Supabase sends the link → session) —
  `frontend/src/auth/`. Live-verified against the real project: an invalid test address and
  a rate-limited real one both surfaced Supabase's actual error text inline; the
  "check your email" success screen itself wasn't exercised live because Supabase's free-tier
  built-in email sender is rate-limited to a handful of sends/hour — the code path is the
  same three-line branch as the two error paths that were verified, not a real coverage gap
- [X] Backend JWT verification on the one write endpoint that needs it (`api-reference.md`:
  "Supabase JWT on write endpoints from Phase 6") — every read endpoint (map, analytics,
  chat, alerts) stays open, unauthenticated, exactly as it is today. `GET /auth/me` is the
  first endpoint to use it — `backend/auth.py` asks Supabase's own `/auth/v1/user` rather
  than decoding the JWT locally (asked, author confirmed): no extra secret to manage, one
  network round-trip per authenticated request, acceptable at this project's traffic

### Saved scenarios (backend + frontend)

- [X] `POST /scenarios` (save the current form config), `GET /scenarios` (list mine),
  `DELETE /scenarios/{id}` — all JWT-gated (`backend/routers/scenarios.py`). Access control is
  Postgres RLS, not backend code: every call forwards the caller's own Supabase token to
  PostgREST (`backend/saved_scenarios.py`) rather than using the service-role key and
  manually filtering by `user_id`. Live-verified against the real project with two throwaway
  test users: user B's list stayed empty while user A had a saved row, and user B deleting
  user A's row 404'd (RLS hides it — the backend can't tell "not found" from "not yours",
  deliberately, so it doesn't leak which is true)
- [X] Frontend: a sign-in affordance (Auth's `SignInMenu`, already built), a "Save scenario"
  action in `src/sections/Scenario.tsx`, and a chip list of saved scenarios — clicking one
  re-runs the real `/scenario` call rather than replaying a stored result. Live-verified
  end to end through the actual UI (a real session injected via localStorage, since driving a
  full magic-link email round-trip isn't automatable): saved a scenario, saw it appear as a
  chip, deleted it, saw the section disappear

### Deployment

- [X] `Dockerfile` for the backend (multi-stage, `uv`-based, existing-image deploy — Render
  never builds from source, `Dockerfile`'s own comment has the why). Several real bloat bugs
  caught and fixed by actually building the image, not assumed: `sentence-transformers`'
  transitive `torch` resolving the CUDA/GPU wheel by default on Linux, `xgboost`'s standard
  wheel bundling `nvidia-nccl-cu12` unconditionally (swapped to `xgboost-cpu`), `uv`'s
  download cache doubling the image layer (BuildKit cache mounts), the container's `CMD`
  re-syncing dev dependencies over the network at every boot (`uv run --no-sync`)
- [X] **First real deploy attempt OOM-killed (exit 137)** — confirmed the RAM risk flagged
  at the dependency-split decision was real, not hypothetical. Traced to
  `backend/routers/agent.py` importing `backend.agents.supervisor` at module level, which
  pulls the full `langchain → chromadb → sentence-transformers → torch` chain in before
  uvicorn even binds a port; `torch`'s runtime alone costs 300–500MB against Render free
  tier's 512MB ceiling. **Fixed via ADR-0013** (asked, author confirmed): RAG embeddings now
  go through Gemini's `gemini-embedding-001` API instead of a local model — `torch` and
  `sentence-transformers` dropped entirely. `chroma_db` rebuilt (incompatible embedding
  dimensions, 384 → 3072). Image now 1.75GB (from 3.22GB); smoke-tested with a hard
  `docker run --memory=512m` limit matching Render exactly — real container, real Supabase
  project, real endpoints (`/health`, `/hotspots`, `/weather`, `/auth/me` and `/scenarios`
  correctly 401, agent supervisor initialized) — settled at 339MB, comfortable margin
- [X] `pyproject.toml` split into base (backend runtime) `dependencies` and a `pipeline`
  optional-dependencies group (`earthengine-api`/`geemap`/`osmnx`/training-and-notebook-only
  tooling) — the Docker image installs the base set only, Render's free tier caps memory at
  512MB
- [X] `render.yaml` blueprint (existing-image `runtime: image`) + `.dockerignore`
- [X] Frontend → Vercel — **[urbanheat-mumbai.vercel.app](https://urbanheat-mumbai.vercel.app)**.
  Two real snags on the way, both fixed live: `VITE_API_BASE_URL` had a trailing slash,
  producing double-slash request URLs (`.../\/city/grid`) that silently broke CORS
  preflighting; Vercel also assigns a separate git-branch alias
  (`urbanheat-mumbai-git-main-*.vercel.app`) distinct from the production domain — a
  different `Origin` than whatever's in `CORS_ORIGINS`, easy to land on by accident via a
  deployment-list link
- [X] Re-push the fixed image to GHCR and redeploy on Render —
  **[urbanheat-api.onrender.com](https://urbanheat-api.onrender.com)**. Two more real snags,
  both fixed live: GHCR packages are private by default (Render's pull 404'd until the
  package visibility was flipped to public), and the first Render service was created as
  "New → Web Service" rather than "New → Blueprint," which builds `Dockerfile` from GitHub
  source directly and fails on the gitignored `COPY`s by design — recreating via Blueprint
  fixed it. Deploy log confirmed a clean boot this time: no OOM, `agent supervisor ready`,
  service live — the ADR-0013 fix held in production, not just in the local 512MB
  reproduction
- [X] `CORS_ORIGINS` updated for the deployed Vercel origin — one more real snag: the value
  had a trailing slash (`.../vercel.app/`), which doesn't literally match the `Origin` header
  browsers actually send (never a trailing slash), so Starlette's CORS middleware 400'd every
  preflight. Diagnosed from the live `OPTIONS` response headers, not guessed
- [X] Set the `BACKEND_URL` GitHub Actions secret — activates the monitoring cron workflow
  that's been correctly built and inert since Phase 4 (`.github/workflows/monitoring.yml`),
  author-confirmed
- [X] CI: `.github/workflows/ci.yml` — `pytest`/`ruff` and `tsc`/`oxlint` on push/PR, distinct
  from the monitoring cron workflow. Runs the pure-logic + mocked-external-service suite only
  (conftest.py's existing skip pattern) — no Earth Engine credentials in CI, by design

### Exit

- [X] ✅ **Public URLs work end-to-end** — author-confirmed 2026-07-29.
  Frontend: <https://urbanheat-mumbai.vercel.app> · Backend:
  <https://urbanheat-api.onrender.com>

---

## Phase 7 — Polish & report · Weeks 23–24+

**Goal:** turn the finished, deployed product into a presentable package — a real
downloadable-report feature, a demo walkthrough with real screenshots, and the written
report draft.

**Settled at kickoff, 2026-07-29**
**The report draft stays outside the public repo** — assembled from `docs/` per
`BLUEPRINT.md` §7's plan and delivered separately, never committed. **Demo script +
screenshots stay in the repo** — a walkthrough of a real, live product reads as confidence,
the opposite problem the report-draft call is solving for.

### Report generation

- [X] `POST /reports/generate` — WeasyPrint PDF for a ward, and a scenario comparison when
  `intervention` is given: mean LST/deviation/population, top SHAP drivers with direction,
  ΔLST + clamping disclosure + the caveat text, all reused from `explain_ward`/`scenario`
  (`backend/services.py`), never recomputed. Returns the PDF directly, not a stored-file URL
  as first sketched (`api-reference.md`'s "Deviation" note has the why). Real bug caught by
  actually building it, not assumed: WeasyPrint needs native Pango/cairo libraries at import
  time that a bare Windows dev machine doesn't have — `Dockerfile` and `ci.yml` both gained
  an `apt-get` step; local tests skip cleanly instead of failing when those libs are absent.
  Live-verified inside the real Docker image with the same `--memory=512m` limit as Phase 6's
  OOM check — real ward A and ward L reports rendered correctly, ward L's numbers matching
  the ones live-verified back in Phase 4
- [X] Frontend: a "Download report" action in the Scenario simulator, using whatever
  ward/intervention/coverage is currently selected — client-side blob download, no stored
  file to link to (matches the backend's own no-storage design)

### Demo & presentation

- [X] `docs/demo.md` — a five-stop walkthrough script (heat map → analytics → scenario →
  copilot → alerts), talking points included, for presenting the live product
- [X] Real screenshots of the deployed dashboard — `docs/screenshots/`, captured against
  **the live URL** with Playwright, not localhost: click-to-explain SHAP drawer, a real
  scenario run with the ΔLST overlay and the new Download-report button, and a real Gemini
  Copilot response (Ward L, citing the exact numbers Analytics and the PDF report also show).
  One honest miss: the weather chart hit a genuine Open-Meteo rate limit
  (`weather_upstream_unavailable`) during capture and is shown in its correctly-degraded
  error state, not force-faked into a success screenshot

### Report draft — outside the repo

- [ ] Assemble the final report from `docs/`: problem/scope (`BLUEPRINT.md`), methodology
  (`ml-methodology.md` + `data-dictionary.md`), design (`architecture.md` + `decisions/`),
  results (notebooks), limitations (the honest notes already kept in `devlog.md`),
  bibliography (`references.md`) — delivered to the author directly, not committed

### Exit

- [ ] ✅ **Report draft complete from `docs/`**

---

## Parked ideas

Second city · SSE live alerts · Marathi/Hindi copilot replies · mobile layout ·
night-time LST from MODIS · air-quality layer (Sentinel-5P)

---

Session details: `docs/devlog.md` · Roadmap rationale: `docs/BLUEPRINT.md`
