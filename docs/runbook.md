# Runbook

Setup from zero, day-to-day operation, deployment, and what to do when things break.

**Status:** Phase 0. Sections for phases not yet built are marked *[Phase N]* and filled in
as they land. Everything below marked ✅ has been verified to work.

---

## 1. External prep — accounts and installs

Do these in order. Earth Engine first: it is the only item with an approval wait.

### 1.1 Google Earth Engine — do this first ⏳

1. Sign in at [earthengine.google.com](https://earthengine.google.com) — **use the college
   email account if available**; institutional addresses verify faster.
2. Register a Cloud project for **noncommercial** use via the registration questionnaire
   (student / academic research).
3. Note the **project ID** → `.env` as `GEE_PROJECT_ID`.
4. Approval is typically minutes to a day. Phase 0's exit criterion is blocked on it;
   nothing else is.

Free under the noncommercial tier with a monthly compute-unit quota (ADR-0001).

### 1.2 Gemini API key

[aistudio.google.com/apikey](https://aistudio.google.com/apikey) → create key → `.env` as
`GEMINI_API_KEY`. Instant, no card. Free tier is Flash-family only (ADR-0002).

### 1.3 Optional — Groq fallback

[console.groq.com](https://console.groq.com) → key → `GROQ_API_KEY`. Instant, free.
Recommended before any demo: one free tier is one point of failure.

### 1.4 Deferred to Phase 6

Supabase · Vercel · Render — all sign in with GitHub, no card.

### 1.5 Installs

| Tool | Why | When |
|---|---|---|
| Python 3.11+ (via [`uv`](https://docs.astral.sh/uv/)) | Everything | Now |
| Node.js LTS (v22+) | Frontend | Now (used Phase 5) |
| Git | ✅ done | — |
| [QGIS](https://qgis.org) | Inspect rasters/GeoJSON, report screenshots | Optional, useful Phase 1 |
| Docker Desktop | Render builds in cloud — local Docker only for debugging | Optional, Phase 6 |

**Hardware** ~10 GB disk · 8 GB RAM workable, 16 GB comfortable · **no GPU needed** ·
stable internet. Heavy raster work runs in Earth Engine's cloud (ADR-0001); the laptop only
handles a ~20k-row table (ADR-0006).

### 1.6 Datasets — almost nothing to download

Landsat, Sentinel-2, WorldCover, WorldPop and SRTM stream through the Earth Engine API.
Open-Meteo and OSM/Overpass need no key. Manual collection is limited to:

- **RAG knowledge base** *(needed by Phase 4, collect anytime)* → `data/knowledge_base/`:
  Mumbai Climate Action Plan · NDMA heat-wave guidelines · WHO heat-health fact sheets ·
  IPCC AR6 urban excerpts · 3–5 UHI papers. All public PDFs. Log each in
  `references.md` as it is added.
- **BMC ward boundaries** — scripted from Datameet/OSM in Phase 1; manual only if that fails.

---

## 2. Local setup

*[Phase 0 — verify and mark ✅ once run end-to-end]*

```bash
git clone https://github.com/DevGurav/urbanheat-mumbai.git
cd urbanheat-mumbai
cp .env.example .env               # fill GEE_PROJECT_ID, GEMINI_API_KEY

uv sync                            # creates .venv, installs the locked dependency set
uv run earthengine authenticate    # opens a browser, once per machine
```

`uv sync` reads `pyproject.toml` and `uv.lock` and provisions Python 3.12 itself — nothing
needs to be installed or activated first, and `uv run` executes inside the venv without
activation. There is deliberately **no `requirements.txt`**: `uv.lock` pins the entire
transitive dependency graph, which is what the "regenerable from scratch" contract in §8
actually requires.

**Python version.** The venv is pinned to 3.12 by `.python-version`, independent of whatever
`python` resolves to on the machine. `geopandas`/`pyproj`/`shapely` wheels lag the newest
CPython releases, and falling back to a source build needs a GEOS/PROJ toolchain that is
painful on Windows. Do not "upgrade" this pin without checking wheel availability first.

Verify the credentials round-trip:

```bash
uv run python -c "import ee, os; from dotenv import load_dotenv; load_dotenv(); ee.Initialize(project=os.environ['GEE_PROJECT_ID']); print(ee.String('ok').getInfo())"
```

Then open `notebooks/00_hello_earth_engine.ipynb` and select the `.venv` (Python 3.12)
kernel.

---

## 3. Running

*[Phase 1+]* Pipeline · *[Phase 3+]* Backend · *[Phase 5+]* Frontend — filled in as built.

```bash
# Pipeline (Phase 1) — deliberate, not on a loop; it spends Earth Engine quota
python -m data_pipeline.run --stage all

# Backend (Phase 3)
uvicorn backend.main:app --reload        # → http://localhost:8000/docs

# Frontend (Phase 5)
cd frontend && npm run dev               # → http://localhost:5173
```

---

## 4. Deployment *[Phase 6]*

Backend → Render (Docker, free) · Frontend → Vercel · DB → Supabase · Cron → GitHub Actions.
Env vars set in each dashboard, never committed. Steps filled in when this is real.

---

## 5. Before a demo — do not skip

1. **Wake the backend** — hit `/health` ~2 min before. Render free sleeps after 15 min idle
   with a ~1 min cold start (ADR-0003). A sleeping service looks like a broken one.
2. **Warm the LLM cache** — run the scripted demo questions once. Cached answers cannot hit
   a rate limit (ADR-0002).
3. **Check the Gemini quota** — ~1,500 req/day resets midnight Pacific. A heavy dev session
   before an evening demo is the realistic way to exhaust it.
4. **Have the local fallback ready** — backend + frontend running locally, in case the
   network or a free tier misbehaves.
5. **Confirm the alerts feed has content** — an empty feed reads as a bug.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ee.Initialize` → permission denied | Project not registered / wrong ID | Check `GEE_PROJECT_ID`; confirm noncommercial registration approved |
| `ee.Initialize` → 403 `SERVICE_DISABLED`, "API has not been used in project … before" | Cloud project exists but was never registered with Earth Engine — creating the project and registering it are separate steps | Register at <https://code.earthengine.google.com/register> (existing project → Unpaid → Academic), or enable `earthengine.googleapis.com` directly in the Cloud console. Wait 1–2 min to propagate |
| `earthengine authenticate` → "This app is blocked" | Institutional Workspace policy blocks that OAuth client. Auth modes use *different* clients, so one mode can work where another is blocked | `uv run earthengine authenticate --auth_mode=notebook`. Paste the code into the prompt of **that same run** — the PKCE verifier is per-session, so a recycled code fails. Else authenticate with a personal Google account granted `Earth Engine Resource Writer` on the project |
| EE task runs forever | Client-side loop over cells; `getInfo()` per cell | Do reductions server-side, export once (ADR-0001) |
| EE quota exhausted | Repeated full-pipeline runs | Wait for monthly reset; cache intermediates in `data/interim/` |
| LST values ~300 | Kelvin, `− 273.15` not applied | `ST_B10 × 0.00341802 + 149.0 − 273.15` |
| LST values ~44,000 | No scale factor applied — raw DN | As above |
| LST values ~0.15 | *Optical* scale factor applied to the thermal band | The two are different: optical is `× 0.0000275 − 0.2`, thermal is `× 0.00341802 + 149.0` |
| Boundary filter matches 0 districts | Admin dataset renamed its districts between versions | Print `ADM2_NAME` values first and correct the list — notebook §2 does this |
| `geemap.Map()` renders blank, no error | `ipyleaflet` widget layer, not Earth Engine | Restart the kernel (widget extensions don't load into a running one); else use `import geemap.foliumap as geemap` |
| Cells missing from composite | Cloud-masked to nothing | Widen year range; flag low-observation cells (`data-dictionary.md` §5) |
| R² suspiciously high (>0.95) | Random split leaking spatial autocorrelation | Use blocked CV (`ml-methodology.md` §2) — this is expected, not a win |
| SHAP says vegetation warms | Model or feature bug | Stop. Investigate before proceeding — physics gate (`ml-methodology.md` §4) |
| Gemini 429 | Free tier ~10 req/min | Backoff; fallback to Groq; cache |
| Gemini 429 all day | Daily 1,500 exhausted | Resets midnight Pacific; use Groq meanwhile |
| Agent states a number no tool returned | Prompt/guardrail failure | Serious — fix before demo (`agents.md` §1) |
| Render first request ~60 s | Free-tier cold start | Expected; wake beforehand |
| Render 5 GB bandwidth warning | `/city/grid` payload | Simplify geometry, gzip, raise cache TTL |
| Supabase project paused | Free tier pauses when idle | Unpause in dashboard; expected over breaks (ADR-0004) |
| Map blank, no errors | CRS mismatch | Storage/API is EPSG:4326; UTM 43N only for area maths |

---

## 7. Key rotation

Keys live only in `.env` (gitignored) and in each host's env settings. To rotate: revoke in
the provider console → issue new → update `.env` and Render/Vercel env → redeploy.
If a key ever lands in a commit, **revoke first, then rewrite history** — revocation is what
actually helps; history rewriting alone does not.

---

## 8. Regenerating everything from scratch

The contract that makes gitignoring data safe (ADR-0004): clone → `.env` → `earthengine
authenticate` → run the pipeline → retrain → everything in `data/processed/` and `models/`
is rebuilt. If this ever stops being true, that is a bug in the pipeline, not a reason to
commit binaries.
