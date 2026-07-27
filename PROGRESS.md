# PROGRESS — UrbanHeat AI

Live task board. Newest phases get expanded into detailed tasks at their kickoff.

**Legend** `[ ]` todo · `[~]` in progress · `[x]` done · ✅ phase exit criterion
**Current phase:** 5 — React dashboard *(Phase 4 complete)*
**Last updated:** 2026-07-27

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
