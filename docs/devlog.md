# Devlog

Engineering journal — one entry per working session, newest first. Written for the future
author: what moved, what broke, what was decided, what to pick up next.

**Why keep this.** By Phase 7 the report needs a narrative — what was tried, what failed,
why the design is what it is. That narrative is impossible to reconstruct from a git log
six months later. Dead ends recorded here are worth as much as successes; a good reviewer asks
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

## 2026-07-29 — Phase 7 — POST /reports/generate: PDF ward reports

**Done**
- `backend/reports/` — `template.html` (Jinja2) + `generate.py` (renders it to PDF bytes via
  WeasyPrint). `backend/routers/reports.py` wires `POST /reports/generate`: always an
  `explain_ward` section, plus a `scenario` comparison section when `intervention` is given.
  Neither computes a number itself — both call the same `backend/services.py` functions
  `GET /explain/{cell_id}` and `POST /scenario` already use, so a PDF can never disagree with
  the live dashboard.
- Returns the PDF directly on the same request (`application/pdf`,
  `Content-Disposition: attachment`), not a stored-file URL as `api-reference.md`'s original
  stub sketched — storing it anywhere would mean adding blob storage this project has never
  needed elsewhere (ADR-0004); streaming the bytes back needs nothing new. Same kind of
  correction Phase 3 already made to other draft contracts in that file.
- Frontend: a "Download report" button in the Scenario simulator, client-side blob URL
  clicked once via a temporary `<a>` and released — no server-side file to link to.

**Broke / learned**
- WeasyPrint installs cleanly via `uv` but needs native Pango/cairo/gdk-pixbuf libraries at
  *import* time, not just the Python package — absent on this Windows dev machine
  (`OSError: cannot load library 'libgobject-2.0-0'`), present via `apt-get` on the deployed
  Debian image and on GitHub Actions' `ubuntu-latest` runner. Asked directly how to handle
  local testing rather than fighting a Windows-specific GTK3 install that wouldn't even
  reflect the real deployment target; author chose Docker-only verification for this feature.
  `Dockerfile` and `ci.yml` both gained the same `apt-get install libpango-1.0-0
  libpangocairo-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libcairo2 fonts-dejavu-core` step.
  The router imports `generate_ward_report` lazily inside the function it needs, not at
  module load — so a machine without these libraries still boots the rest of the app fine;
  only this one endpoint 503s (`reports_unavailable`), matching how the RAG retriever already
  degrades when its own optional dependency is missing (ADR-0013).
- Real test-authoring bug caught before it shipped: `from backend.reports.generate import
  generate_ward_report` binds a local name in `backend.routers.reports`, so
  `monkeypatch.setattr` on the *source* module (`backend.reports.generate`) silently didn't
  reach what the router actually calls — three tests passed for the wrong reason until a
  real assertion failure (503 instead of 200) exposed it. Fixed by patching
  `backend.routers.reports.generate_ward_report`, where the router actually looks it up.
- Live-verified inside the real Docker image, under the same `--memory=512m` limit as Phase
  6's OOM check, against the real Supabase project: ward A (a cooling ward, −1.25 °C
  deviation) and ward L (the known hottest ward, +3.22 °C — the exact number live-verified
  back in Phase 4's agents build) both rendered correct PDFs. First render spilled a nearly
  empty second page onto the output; iterated the template's CSS directly inside the running
  container via `docker cp` (no full rebuild per change) until it fit cleanly on one page.

**Next**
- Demo script + real screenshots of the deployed dashboard, then the report draft itself
  (assembled from `docs/`, delivered outside the repo per the kickoff's own call).

---

## 2026-07-29 — Phase 7 — Kickoff: report generation, demo, report draft

**Done**
- Planning pass before code, per the working agreement. Read `PROGRESS.md`'s thin Phase 7
  stub against `BLUEPRINT.md` §7's documentation-system plan and `api-reference.md`'s
  existing `POST /reports/generate` stub, then expanded the board into three groups: report
  generation (the real feature), demo & presentation, and the report draft itself.
- One real scoping question, asked directly: should the final written report/paper draft
  live in the public repo, or stay separate? Author chose separate — delivered outside the
  repo once assembled, never committed. Demo script + screenshots stay in the repo, the
  opposite call for the opposite reason: a walkthrough of a real, live, deployed product
  reads as confidence, not coursework, which is exactly the concern the report-draft call
  was solving for.

**Decided (author-confirmed)**
- Report draft: outside the repo, not committed.
- Demo script + screenshots: in the repo.

**Next**
- Build `POST /reports/generate` — WeasyPrint PDF for a ward or scenario, then the frontend
  "Download report" action.

---

## 2026-07-29 — Phase 6 — Closed: public URLs live

**Done**
- Frontend live at [urbanheat-mumbai.vercel.app](https://urbanheat-mumbai.vercel.app), backend
  at [urbanheat-api.onrender.com](https://urbanheat-api.onrender.com). Author pushed the fixed
  (post-ADR-0013) image, redeployed, and confirmed the dashboard loads real data end to end.
  Phase 6 exit criterion — public URLs work — author-confirmed.
- Four more real bugs, found and fixed live during the actual deploy, none of which the
  local `docker run --memory=512m` reproduction (previous entry) could have caught, since
  they're all about the boundary *between* deployed services, not any one container's own
  behavior:
  - Magic-link sign-in redirected to `localhost:3000` — Supabase only redirects to an
    allow-listed URL (**Authentication → URL Configuration**) and silently falls back to its
    factory-default Site URL otherwise; `emailRedirectTo: window.location.origin` in the
    frontend code was never consulted. Fixed by setting the real Site URL and adding both the
    production and local-dev origins to the Redirect URLs allow-list.
  - `VITE_API_BASE_URL` had a trailing slash → every request URL came out
    `.../\/city/grid` (double slash) → silently broke CORS preflighting, since `//city/grid`
    isn't the same path as `/city/grid` to FastAPI's router.
  - GHCR packages are private by default — Render's pull 404'd
    (`image "..." not found`) until the package visibility was flipped to public. The image
    has no secrets baked in (those arrive as env vars at runtime), so public is the right
    choice here, not a compromise.
  - The first Render service was created via "New → Web Service," which builds `Dockerfile`
    from the GitHub source directly and fails on the gitignored `COPY`s by design
    (`Dockerfile`'s own comment already explains why) — recreating via "New → Blueprint" (the
    path that actually reads `render.yaml`'s `runtime: image`) fixed it.
  - `CORS_ORIGINS` itself also had a trailing slash — `https://urbanheat-mumbai.vercel.app/`
    doesn't literally match the `Origin` header a browser sends (never a trailing slash by
    spec), so Starlette's CORS middleware 400'd every preflight with no
    `Access-Control-Allow-Origin` header. Diagnosed conclusively from the live OPTIONS
    response headers in DevTools, not guessed — the same request that failed against the
    trailing-slash value succeeded immediately after removing it.
- Closed out the phase across docs: `PROGRESS.md` (all Deployment checkboxes + exit
  criterion ticked, current phase bumped to 7), `CHANGELOG.md` (Phase 6 entry),
  `architecture.md` (Deployment diagram and the Frontend/Backend subgraphs marked ✅ with the
  live URLs), `BLUEPRINT.md` (stale Groq mention in the risk register), `README.md` (was
  still describing Phase 0 and "not yet runnable" — never updated across five phases;
  rewritten to match current reality), version bumped to 1.0.0
  (`pyproject.toml`/`backend/main.py`) per `CHANGELOG.md`'s own stated phase→version mapping.

**Broke / learned**
- Every one of this session's five real deploy-time bugs (the OOM, the two trailing slashes,
  the private GHCR package, the wrong Render service type) was invisible to every form of
  testing this project did *before* deploying — local dev, the full pytest suite, even the
  hard `--memory=512m` Docker reproduction. They only exist at the seam between two actually-
  separate deployed services talking over a real network, which nothing short of an actual
  deploy exercises. Worth remembering for the report: "tested locally" and "works when
  deployed" are different claims, and the gap between them is exactly where this session's
  bugs lived.

**Next**
- Phase 7 — polish and report: PDF report endpoint, final report/paper draft, presentation prep.

---

## 2026-07-28 — Phase 6 — First deploy attempt OOM-killed; fixed via ADR-0013

**Done**
- Author pushed the image to GHCR and deployed via Render successfully — both real firsts.
  Hit two configuration snags immediately, both fixed live: GHCR packages are private by
  default (Render's pull 404'd until the package visibility was flipped to public), and the
  first Render service was created as "New → Web Service" rather than "New → Blueprint,"
  which builds `Dockerfile` from GitHub source directly and fails on the gitignored `COPY`s
  by design (`Dockerfile`'s own comment already explains why that path can't work) —
  recreating via Blueprint fixed it.
- With both fixed, the container actually started pulling and running — then died with
  `Exited with status 137` a few seconds after logging `loading artifact store…`. 137 is
  SIGKILL. Diagnosed from the code before touching anything: `backend/routers/agent.py`
  imports `backend.agents.supervisor` at module level, so importing `backend.main` — before
  uvicorn even binds a port — pulls in `langchain → chromadb → sentence-transformers →
  torch` unconditionally. `torch`'s runtime alone typically costs 300–500MB resident, against
  Render free tier's 512MB ceiling. This is exactly the RAM risk flagged (and left open) when
  the `pyproject.toml` dependency split was decided a few tasks ago — now confirmed real, not
  hypothetical.
- Presented the real options (pay for a bigger Render tier vs. swap the local embedding model
  for an API-based one) and asked; author chose the API swap. Wrote ADR-0013:
  `backend/rag/ingest.py`/`retrieve.py` now embed via `GoogleGenerativeAIEmbeddings`
  (`gemini-embedding-001`), same `GEMINI_API_KEY` already in use, no new credential.
  `torch`/`sentence-transformers` dropped from `pyproject.toml` entirely (`uv lock` also
  dropped `transformers`, `sympy`, `safetensors`, `regex`, `mpmath` — none needed elsewhere).
  `chroma_db` rebuilt from scratch (dimensions changed 384 → 3072, not additive) — 28 chunks
  re-embedded in 2 batched `batchEmbedContents` calls, not 28 separate ones.
- `docs/agents.md`'s RAG line explicitly said "never a paid embedding API" — that was a real
  Phase 4 design principle, and this reverses it. Said so directly in both the doc and
  ADR-0013 rather than quietly editing the line away.

**Broke / learned**
- Confirmed the fix with a hard local reproduction, not just a rebuild-and-hope:
  `docker run --memory=512m --memory-swap=512m ...` against the new image, watched
  `docker stats` through `/health`, `/hotspots`, `/weather`, `/auth/me` (401 with no token),
  `/scenarios` (401), and the agent supervisor initializing — settled at 339MB against the
  512MB limit. Image size 1.75GB, down from 3.22GB.
- One real, disclosed open question, written into ADR-0013 rather than glossed over: whether
  `gemini-embedding-001` shares the same scarce 20 req/day quota as `gemini-flash` chat
  calls (ADR-0011), or has its own separate limit, is **not confirmed** — Google doesn't
  publish free-tier per-model numbers, only "check AI Studio's dashboard." Same
  honest-uncertainty position the original ~1,500/day chat estimate was in before a real 429
  corrected it in production.

**Next**
- Re-push the fixed image to GHCR and redeploy on Render (`runbook.md` §4.1–4.2, author's own
  action) — the previous push had the OOM bug baked in. Then Vercel (§4.3), close the
  `CORS_ORIGINS`/`BACKEND_URL` loop (§4.4), and the Phase 6 exit criterion is the author's to
  confirm.

---

## 2026-07-28 — Phase 6 — Deployment: Dockerfile, CI, render.yaml (image built, not yet pushed)

**Done**
- Split `pyproject.toml`'s single dependency list into base `dependencies` (what
  `backend/main.py`'s import graph actually needs) and a `pipeline` optional-dependencies
  group (`earthengine-api`, `geemap`, `osmnx`, `lightgbm`, `shap`, notebook tooling, the
  unused-since-ADR-0011 `langchain-groq`, the never-imported `pypdf`) — asked first, author
  picked the split over shipping everything, since Render's free tier caps memory at 512MB
  and `sentence-transformers` alone already spends real margin against that.
- `Dockerfile` — multi-stage, `uv`-based, installs the base set only. Bakes in the gitignored
  `data/processed/*`, `models/*`, and `backend/rag/chroma_db/` this project has never
  committed (ADR-0004) — asked first, author picked "build and push a pre-built image
  locally" over "regenerate artifacts in Render's build," since neither Render nor GitHub
  Actions has Earth Engine credentials or the compute quota to do that, and ADR-0004 already
  frames "regenerate" as the author's own deliberate action, not CI's.
- `render.yaml` (existing-image blueprint), `.dockerignore`, `.github/workflows/ci.yml`
  (pytest/ruff + tsc/oxlint on push/PR — distinct from `monitoring.yml`'s cron trigger).
- Rewrote `runbook.md` §4 with the real deploy sequence (backend → frontend → close the
  CORS/BACKEND_URL loop) and fixed two stale entries found while touching the file: §1.3
  still called the (already-dropped, ADR-0011) Groq key "recommended," and the troubleshooting
  table still said "fallback to Groq" / "Daily 1,500 exhausted" for Gemini 429s — both
  superseded earlier this same phase (§1.3, §5.3) but never propagated here.

**Broke / learned — all caught by actually building and running the image, not assumed**
- `sentence-transformers`' transitive `torch` resolved the CUDA/GPU wheel by default on
  Linux — `docker history` showed a single layer at 3.94GB, dominated by ~20 `nvidia-*`
  packages (cudnn, cusparselt, nccl, cufft, cusolver, ...) totally unusable on Render's
  CPU-only free tier. Fixed via `tool.uv.sources` pinning `torch` to
  `download.pytorch.org/whl/cpu` — but this only took effect once `torch` was listed as a
  *direct* dependency; uv does not honor a source override for a name that only ever
  appears transitively.
- `xgboost`'s standard wheel bundles `nvidia-nccl-cu12` (289MB) unconditionally on Linux, for
  distributed multi-GPU training this solo-laptop project has never used (ADR-0006 chose
  gradient-boosted trees partly to avoid exactly this kind of infra). Swapped to
  `xgboost-cpu` — an official minimal build from the same maintainers, same `import xgboost`
  namespace, confirmed via PyPI's own package description before trusting the swap.
- `uv`'s own download cache was sitting in the same image layer as the installed packages —
  a 3.94GB layer against a 2.1GB actual `.venv`, nearly 2GB of pure waste. Fixed with
  BuildKit `--mount=type=cache` on both `uv sync` steps, so the cache lives outside the
  image entirely.
- The container's `CMD` used plain `uv run uvicorn ...`, which re-syncs the environment
  against `pyproject.toml` at *every* container start — with none of the build's
  `--frozen --no-dev` flags, so it happily installed `ruff` (a dev-only tool) over the
  network on every boot. Caught by reading the smoke-test container's own startup log, which
  showed `Downloading ruff` where nothing should have downloaded at all. Fixed with
  `uv run --no-sync`.
- The RAG embedding model (`sentence-transformers/all-MiniLM-L6-v2`) was re-downloading from
  HuggingFace at every cold start — ~34s of the container's startup spent on HTTP calls to
  `huggingface.co`, stacking on top of Render's own free-tier cold start. Pre-warmed the
  model into the image at build time and set `HF_HUB_OFFLINE=1` at runtime; the same
  container went from "agent supervisor ready" at +34s to +0s (no HF log lines at all on the
  rebuild).
- End state: image builds cleanly at 3.22GB (down from an initial 5.29GB, most of the
  remainder legitimate weight — torch-cpu, chromadb+onnxruntime, the geopandas stack, not
  waste), smoke-tested with the real `.env` against the live Supabase project:
  `/health`/`/hotspots`/`/weather`/`/explain` served real data, `/auth/me` and `/scenarios`
  correctly 401'd with no token, and the agent supervisor initialized (without spending a
  real Gemini call — confirmed via the startup log's "agent supervisor ready" line, not by
  actually hitting `/agent/chat`).
- Also caught, unrelated to Docker: `data_pipeline/config.py`'s `gee_project_id` had no
  default, meaning `Settings()` — which the backend also depends on — would refuse to
  instantiate without it, crashing the deployed backend on startup over a field it never
  reads. Given an empty default like every other Phase 4+ credential.

**Next**
- Actually pushing the image to GHCR and creating the Render/Vercel services is the author's
  own action (`runbook.md` §4.1–4.3) — same pattern as every other external account this
  project has needed. Once both exist: close the `CORS_ORIGINS`/`BACKEND_URL` loop (§4.4) and
  the Phase 6 exit criterion — public URLs working end to end — is the author's to confirm.

---

## 2026-07-28 — Phase 6 — Saved scenarios (RLS-backed CRUD, live-verified)

**Done**
- `backend/saved_scenarios.py` — `list_saved_scenarios`/`create_saved_scenario`/
  `delete_saved_scenario` over PostgREST, one `requests` call each (same client the rest of
  the backend already uses, no `supabase-py` SDK added). Every call forwards the caller's own
  access token (`AuthUser.access_token`, added to the dataclass this task) rather than the
  service-role key — Postgres RLS (`supabase/schema.sql`'s three policies) is the actual
  access-control boundary, not a `WHERE user_id = ...` this code would have to get right
  itself. `DELETE` can't distinguish "no such row" from "someone else's row" — RLS just
  returns zero rows either way — and the router intentionally preserves that ambiguity as a
  404 rather than trying to tell the two apart.
- `backend/routers/scenarios.py` — `GET`/`POST`/`DELETE /scenarios`, all
  `Depends(get_current_user)`-gated. `main.py`'s CORS `allow_methods` needed `DELETE` added
  (was `GET, POST` only since Phase 3).
- Frontend: `api/client.ts` gained the three calls (each takes an access token, forwarded as
  a bearer header) and `request()` learned to treat `204` as "no body" rather than trying to
  `.json()` an empty response. `Scenario.tsx` gained a "Save scenario" button and a chip list
  — click a chip to load its config and re-run the real `/scenario` call, click its delete
  icon to remove it. Both only render when signed in (`accessToken !== null`), same
  hide-don't-break pattern as `SignInMenu`.
- 14 new backend tests (`tests/test_saved_scenarios.py`), all mocking PostgREST.

**Broke / learned**
- Live-verified the RLS boundary itself, not just the code path: created two throwaway
  Supabase users via the admin API (service-role key, `email_confirm: true`, no real email
  sent), signed both in via the password grant, and hit the running backend directly. User
  B's list stayed empty while user A had a saved row; user B trying to delete user A's row by
  id got a 404, not a 403 or a silent no-op — confirming the "not found vs not yours"
  ambiguity is real Postgres behavior, not just what the backend claims. Deleted both test
  users afterward (cascades removed their rows too).
- Live-verified the actual frontend, not just the API, by injecting a real Supabase session
  into `localStorage` under its default `sb-<project-ref>-auth-token` key before page load
  (driving a full magic-link email round-trip isn't automatable) — confirmed sign-in state,
  the Save button, saving a scenario, the chip appearing, and deleting it, all through the
  real UI against the real backend and the real Supabase project. Cleaned up the test user
  afterward the same way.
- MUI version mismatch caught by `tsc`, not at runtime: `@mui/icons-material/DeleteOutline`
  doesn't exist in the installed version (only `DeleteOutlineOutlined`/`Rounded`/`Sharp`/
  `TwoTone` variants) — switched to the plain `Delete` icon, which does exist. `Stack`'s
  `flexWrap`/`useFlexGap` props also aren't in this version's types; moved both into `sx`.

**Next**
- Deployment: `Dockerfile` → Render, frontend → Vercel, `CORS_ORIGINS` for the deployed
  origin, `BACKEND_URL` GitHub Actions secret, a CI workflow (pytest/ruff/tsc/oxlint).

---

## 2026-07-28 — Phase 6 — Auth: magic-link sign-in and JWT verification

**Done**
- `backend/auth.py`'s `get_current_user` — verifies a bearer token by asking Supabase's own
  `GET /auth/v1/user` rather than decoding the JWT locally (asked, author confirmed: no extra
  secret beyond the anon key already in `.env`, at the cost of one network round-trip per
  authenticated request — an acceptable trade at this project's traffic, and consistent with
  dropping the Groq fallback for the same reason, ADR-0011).
- `GET /auth/me` — the first endpoint the dependency actually gates; echoes `{id, email}`.
  Nine new tests (`tests/test_auth.py`), all mocking `requests`/`get_settings` so none depend
  on a live Supabase project.
- `data_pipeline/config.py` gained `supabase_url`/`supabase_anon_key`/`supabase_service_key`,
  empty-default like every other Phase 4+ credential (a fresh clone still boots).
- Frontend: `src/lib/supabase.ts` (client, `null` if the two `VITE_` vars aren't set — every
  read-only section still works without a Supabase project), `src/auth/AuthProvider.tsx`
  (session state, `signInWithOtp`, `signOut`), `src/auth/SignInMenu.tsx` in the AppBar.
- `frontend/vite.config.ts` got `envDir: '..'` — the frontend had no working env file at all
  before this (no `frontend/.env` existed; `VITE_API_BASE_URL` only ever read its hardcoded
  fallback). One root `.env` now feeds both backend and frontend, matching what
  `.env.example` already documented.
- `pyproject.toml`: `extend-immutable-calls = ["fastapi.Depends", "fastapi.Query"]` — ruff's
  B008 flagged `Depends()` in an argument default (FastAPI's own DI idiom); more
  `Depends(get_current_user)` call sites are coming with the saved-scenarios endpoints.

**Broke / learned**
- The value the user pasted into `SUPABASE_URL` turned out to be a `sb_publishable_...`
  key, not a URL — Supabase's redesigned dashboard puts the "publishable key" (its newer name
  for the anon key) right next to the Project URL field. Caught immediately on first real
  page load: the Supabase JS client throws `Invalid supabaseUrl` synchronously, not a silent
  failure. Fixed without asking for a re-paste — decoded the (non-secret, structural) `ref`
  claim out of the anon/service JWTs already correctly in `.env` and reconstructed
  `https://{ref}.supabase.co` directly; cross-checked their `role` claims (`anon` /
  `service_role`) to confirm those two fields were assigned correctly before trusting the fix.
- Live-verified end to end against the real project once the URL was fixed: an obviously-fake
  test address and a real one (rate-limited after one send) both surfaced Supabase's actual
  error text inline through the UI. The "check your email" success screen itself wasn't
  triggered live — Supabase's free-tier built-in email sender allows only a handful of
  sends/hour — but that branch is the same three-line no-error path already exercised by
  both error cases reaching the same call site, not an untested code path.
- CORS errors appeared in the browser console during verification (`localhost:5174` vs the
  `CORS_ORIGINS` default of `5173`) — a leftover dev server from an earlier task had port
  5173 pinned, pushing this session to 5174. Not a real bug; killed the stale process.

**Decided**
- JWT verification method: remote check against Supabase's Auth API, not local decode with a
  fourth secret (`SUPABASE_JWT_SECRET`) — asked directly, author chose the recommended option.

**Next**
- Saved scenarios: `POST /scenarios` / `GET /scenarios` / `DELETE /scenarios/{id}`, all
  `Depends(get_current_user)`-gated, plus the frontend save/list UI in `Scenario.tsx`. Then
  Deployment.

---

## 2026-07-28 — Phase 6 — Supabase schema and RLS

**Done**
- Wrote `supabase/schema.sql` — the `saved_scenarios` table (config-only columns matching
  `ScenarioRequest` exactly, `intervention`/`coverage` check constraints so a row can never
  describe a scenario the backend would reject), an index on `user_id`, RLS enabled, and
  three policies (select/insert/delete, all `auth.uid() = user_id`). No update policy —
  save/list/delete is the whole task, per the kickoff's own scoping.
- Rewrote `runbook.md` §1.4 from a placeholder into real steps: create the Supabase project,
  run `schema.sql` in the dashboard's SQL editor, copy the three keys into `.env`.

**Broke / learned**
- Re-reading `architecture.md`'s Components diagram against ADR-0012 (alerts stay
  file-based, decided at the Phase 6 kickoff) turned up a real inconsistency it introduced:
  the diagram still routed `A4 → NTF → SUPA`, i.e. Monitoring's alert output flowing to
  Supabase, which ADR-0012 had already overturned. Added an `alerts.jsonl` storage node and
  re-pointed the arrow there instead; relabelled `SUPA` to drop "alerts" from what it holds.
  Same issue in `agents.md` §7's Agent 4 write-up, which still said alerts go
  "file (Phase 4) → Supabase (Phase 6)" — fixed to cite ADR-0012 instead. Neither was code,
  so nothing was broken at runtime, but both would have misled a reviewer reading the
  diagrams against the actual decision.
- Also updated the Deployment diagram (§6) to mark Supabase 🟨 "schema written, not
  provisioned" instead of ⬜, matching how the rest of the diagram already distinguishes
  "built locally" from "actually deployed."
- While rewriting `runbook.md` §1.4, noticed §1.3 still called Groq "recommended before any
  demo" — stale since ADR-0011 dropped the Groq fallback in Phase 4. Corrected it to say
  what's actually true: `GROQ_API_KEY` is scaffolded but unused.

**Next**
- Actually creating the Supabase project and running `schema.sql` against it is the author's
  own action (same pattern as Earth Engine/Gemini in Phase 0) — can't be verified from here
  until that's done and the three keys are in `.env`.
- Then: Auth (magic-link sign-in, backend JWT verification), Saved scenarios endpoints +
  frontend UI, Deployment.

---

## 2026-07-28 — Phase 6 — Kickoff: persistence, auth, deployment planning pass

**Done**
- Planning pass before code, per `BLUEPRINT.md` §8. Re-read ADR-0004 (which already scoped
  Supabase for users/saved-scenarios/alerts back in Phase 0), `.env.example`'s existing
  Supabase/SMTP scaffolding, and `api-reference.md`'s "Supabase JWT on write endpoints"
  line. Expanded the Phase 6 board into schema/RLS, Auth, saved-scenarios, and deployment
  groups.
- Wrote ADR-0012, a **partial** revision of ADR-0004 — not a reversal. Users and saved
  scenarios still move to Supabase exactly as ADR-0004 scoped; only alert history's
  disposition changes. Appended a dated pointer note to ADR-0004 itself (the one permitted
  edit — annotates, doesn't alter the original argument) rather than editing its body.

**Decided (author-confirmed, all three recommended)**
- **Saved scenarios store config only** (ward, intervention, coverage, user, timestamp), not
  a full result snapshot. Loading one re-runs the real `/scenario` call — always fresh,
  never silently stale against a retrained model.
- **Auth is Supabase's magic-link/email-OTP flow**, not GitHub OAuth. No OAuth app to
  register, and it fits the actual named user base (`architecture.md` §1: municipal
  authorities, planners, NGOs) better than requiring a GitHub account.
- **Alerts stay file-based** (ADR-0012). Built in Phase 4, they turned out to fit ADR-0004's
  own "analytical, read-only, regenerable" category — public, city-wide, cron-written, never
  user-owned — not its "transactional" one. Moving them to Postgres now would be real
  migration work (and a second free-tier idle-pause risk) for no new capability;
  `GET /alerts` already works correctly against the file.

**Next**
- Supabase project + schema: `saved_scenarios` table, RLS scoped to `auth.uid()`. Then Auth
  wiring (backend JWT check, frontend magic-link flow) before the save/list/delete endpoints
  that depend on it.

---

## 2026-07-28 — Phase 5 — Close-out

**Done**
- Author clicked through the full app in one sitting and confirmed the exit criterion: ✅
  *Full end-to-end local demo*. Everything the five per-section live checks this phase
  already showed individually now stands confirmed as one coherent thing, not five
  disconnected pieces.
- `docs/CHANGELOG.md` gets the Phase 5 entry — the frontend stack, the five sections, the
  cross-checks between independent code paths landing on identical real numbers, the three
  real bugs caught by screenshots rather than by `tsc`/lint, and the limitations carried
  forward (no frontend test suite by design, the unreachable `clamped` warning path, no chat
  memory, nothing deployed yet).
- `docs/architecture.md` updated to reality: the Frontend subgraph and all five of its nodes
  are ✅ in the Components diagram; the deployment diagram's Vercel node is 🟨 (built
  locally, not deployed) — the same "built but not live yet" language already used for the
  backend and the monitoring cron. The top status paragraph now says the whole local stack
  runs end to end, and that Phase 6 is entirely about the gap to public URLs, not new surface.
- `PROGRESS.md` rolled to Phase 6.

**Next**
- Phase 6 kickoff: Supabase (users, alerts, saved scenarios) + Auth, then Dockerize the
  backend for Render and the frontend for Vercel. A planning pass before code, per
  `BLUEPRINT.md` §8, same as every prior phase kickoff — real decisions here too (RLS policy
  shape, what "saved scenario" actually persists, whether alerts move to Supabase now or stay
  file-based a while longer).

---

## 2026-07-28 — Phase 5 — Alerts feed (all five sections done)

**Done**
- `src/sections/Alerts.tsx` — `GET /alerts` polled every 5 minutes (ADR-0003), severity-coded
  cards, an honest empty state. Removed the now-orphaned `Placeholder.tsx` — all five
  sections are real components now, nothing left placeholder-ing anything.
- Severity color is the dataviz skill's **Status** job, not sequential or categorical:
  advisory/heat_wave/severe_heat_wave map to warning/serious/critical from
  `references/palette.md`, each always paired with an icon + label (`STATUS` added to
  `src/viz/color.ts`) — the skill is explicit that status color never carries meaning alone.
- Verified both real states. Empty: genuinely true right now (`read_alerts()` returns `[]`
  — no real alert has ever fired). Populated: wrote 3 realistic entries (one per severity,
  matching `backend/agents/alerts.py`'s exact JSONL shape) directly into the gitignored
  `data/processed/alerts.jsonl`, screenshotted the escalating color-coding and newest-first
  order rendering correctly, then deleted the file again — verifying the UI without leaving
  fake data sitting in a state file that's supposed to reflect reality.

**Decided**
- The fake alerts got deleted after the screenshot, not left in place. `alerts.jsonl` is
  gitignored so it was never going to reach the repo either way, but leaving fabricated
  "the city had a severe heat wave" entries in *local* state — even temporarily, even
  file-based — sat wrong against this project's whole stance on invented numbers. Verify,
  then restore honest state, same as any other test fixture.

**Broke / learned**
- Nothing broke this entry. Worth noting for next time instead: `run_in_background: true` on
  the Bash tool (rather than shell `&`/`disown`) was the fix for the backend/frontend-launch
  flakiness noted two entries back — used consistently for the rest of Phase 5's live
  verifications and it was reliable every time.

**Next**
- All five Phase 5 sections are built and individually verified live. What's left is the
  phase exit criterion itself: ✅ *Full end-to-end local demo* — clicking through the whole
  app in one sitting, author-verified, not assumed from five separate section checks. Not
  ticked here, per convention.

---

## 2026-07-28 — Phase 5 — Copilot chat

**Done**
- `src/sections/Chat.tsx` — a local turn history (user/assistant/error bubbles), `POST
  /agent/chat`, a collapsed-by-default tool-call disclosure per reply, an optional map for a
  returned `layer`, and a persistent info banner naming the real 20 req/day quota
  (`BLUEPRINT.md`) up front rather than only surfacing it after a request fails.
- Distinct handling for the two 503s `api-reference.md` documents:
  `agent_layer_unavailable` ("not configured at all") vs. `agent_upstream_unavailable`
  ("configured but the call failed — likely quota") get different messages, since they mean
  different things and imply different next steps for whoever's looking at the screen.
- Deliberately spent exactly **one** real LLM call to verify this: "Which ward in Mumbai is
  hottest?" → Copilot → `get_hotspots` + `explain_ward` → Ward L, 43.18 °C — the same fact
  independently confirmed four separate times now this phase (the live agent smoke test, the
  Analytics HVI ranking, the Scenario simulator, and now the chat UI), each through a
  different code path. Re-sent the identical question after the markdown fix below and got a
  cache hit (near-instant, zero new tool calls) — confirmed `Supervisor`'s response cache
  works, essentially for free, as a side effect of re-verifying the UI fix.

**Decided**
- Added `react-markdown` — not in the original task list, but found live: the real Copilot
  reply came back full of `**bold**` and `### headers` rendered as literal asterisks and
  hashes, since `Typography` was just printing the raw string. Every real Copilot/Planning
  response uses markdown heavily (seen consistently since the first live agent test), so this
  wasn't cosmetic — it affected every single reply's readability. Small, standard, scoped
  to exactly this rendering concern.

**Broke / learned**
- Nothing broke in the application code this entry — the two real bugs this session (the
  markdown rendering, confirmed above) were caught and fixed in the same pass. Worth noting
  instead: local dev tooling friction, not app bugs — `uv run uvicorn ... &` backgrounded via
  plain shell `&`/`disown` silently failed to redirect output on this Windows/Git-Bash setup
  more than once (empty log files, but the process was sometimes still actually running and
  bound to the port underneath the failed-looking check). Switching to the Bash tool's own
  `run_in_background` for both the backend and the dev server fixed the flakiness for the
  rest of this session — worth remembering for Alerts, next.

**Next**
- Alerts feed: `GET /alerts` polling list, severity-coded, an honest "no active alerts" empty
  state — the last of the five sections. Then the Phase 5 exit criterion: a full end-to-end
  local demo, author-verified.

---

## 2026-07-28 — Phase 5 — Scenario simulator

**Done**
- `src/sections/Scenario.tsx` — ward + intervention + coverage form, `POST /scenario`, a
  ΔLST summary, a prominent `clamped` warning `Alert`, the returned `caveat`, and a small
  embedded map coloring just the affected cells by cooling magnitude.
- The ward dropdown reuses `useHotspots(24, "hvi", "ward")` instead of a new "list wards"
  endpoint — the backend has no such endpoint, and 24 is every ward, so a ranking call with
  a high `n` is an honest way to enumerate them without adding backend surface for a dropdown.
- The map overlay solves a real gap: `/scenario` returns `cell_id` + `dlst` only, no geometry.
  Joined client-side against `/city/grid`'s features by `cell_id` — the same join
  `backend/agents/supervisor.py`'s `build_agent_layer` already does server-side for
  `/agent/chat`, just done in the browser here since the plain REST endpoint doesn't do it.
- Verified live: Ward L greening (391 cells, mean −1.03 °C, best −3.59 °C) and cool-roof at
  100% (mean −2.38 °C, best −3.40 °C) **matched exactly** the numbers the live-verified
  Planning agent produced for the same ward earlier this phase — two independent paths (this
  UI's `/scenario` HTTP call vs. the agent's `simulate_scenario` tool call) landing on
  identical numbers is a real cross-check, not a coincidence worth ignoring. Coverage slider
  correctly disables for greening, enables for cool-roof. Zero console errors.

**Decided**
- Sequential, not diverging, color for the ΔLST overlay. `dlst` is always ≤ 0 — greening is
  floored at 0 (`ml/scenario.py`, "greening cannot warm a cell all-else-equal") and cool-roof
  is a cited coefficient that only cools — so this is a one-directional magnitude (how much
  cooling), not a polarity question. Reused `sequentialScale` from the heat map rather than
  reaching for the diverging pair just because temperature is involved.

**Broke / learned**
- Tried to verify the `clamped` `Alert` actually renders, not just that its JSX is correct.
  Queried `/scenario` directly for greening across all 24 real wards — every one came back
  `clamped_cells: 0`. Cool-roof never clamps by construction (a formula, not a model call).
  So the warning path is real code, verified by review, but genuinely unreachable with the
  current dataset — recorded as an honest gap in PROGRESS.md rather than claiming a live
  trigger that didn't happen. If a future data refresh or a wider coverage range ever does
  clamp a real ward, that's the moment to screenshot it for real.

**Next**
- Copilot chat: `POST /agent/chat`, tool-call transparency, the multi-second thinking state,
  and honest handling of both 503s plus the real 20 req/day quota — the section most likely
  to actually hit that limit live.

---

## 2026-07-28 — Phase 5 — Analytics

**Done**
- `src/sections/Analytics.tsx` — three panels. Hotspots: `/hotspots` with `hvi`/`lst` and
  `ward`/`cell` toggles, a horizontal Recharts bar chart plus an MUI table (the dataviz
  skill's "table view exists" accessibility pass, and a real second reading of the same
  numbers). Weather: a 7-day max/min line chart. Trends: the backend's own honest stub
  message, not hidden or faked.
- `src/viz/color.ts` gained `CATEGORICAL` — the palette's first 3 slots (blue, orange, aqua),
  enough for this project's 2-series weather chart without touching the all-pairs cap the
  skill documents for choropleths/scatter (3 slots max there too, coincidentally the same
  number for a different reason).
- Verified live: backend + frontend both actually running. HVI ward ranking (B, L, C, H/E,
  F/S, K/E, G/N, E, M/W, G/S) matched Phase 2's own recorded ranking
  (`data-dictionary.md`) exactly — a real cross-check against prior work, not just "did a
  bar render." LST/cell toggle re-fetched and re-rendered correctly (top cell 50.63 °C, in
  range with Phase 0's known max ~51.6 °C). Weather chart showed real forecast dates and
  a sensible max>min ordering throughout. Trends stub text matched the backend's note
  verbatim. Zero console errors.

**Decided**
- One color for the hotspots bar chart, not one per bar. It's a single series (rank by
  HVI or LST value) — the dataviz skill's color-formula is explicit that a single series
  needs no legend and no per-item hue; coloring bars individually would spend the identity
  channel on data the axis labels already carry.
- Weather's max/min color assignment (orange/blue) is fixed by convention, not re-derived
  per render — "which series is orange" never changes based on what the data looks like
  that day, which is what keeps a fixed categorical assignment legitimate rather than
  arbitrary.

**Broke / learned**
- The ranking chart's Y-axis `width` was hardcoded to fit ward codes ("B", "H/E" — short).
  Cell IDs are 11-digit numbers; toggling to cell view silently truncated them
  ("549001410" instead of "10549001410") — caught by actually reading the toggled
  screenshot, not by `tsc` or lint, since a hardcoded pixel width that's merely "too small"
  is not a type error. Fixed by keying the width off `unit`.

**Next**
- Scenario simulator: ward + intervention + coverage form → `POST /scenario`, ΔLST summary,
  per-cell map overlay, the `clamped` disclosure surfaced prominently.

---

## 2026-07-27 — Phase 5 — Heat map

**Done**
- `src/sections/HeatMap.tsx` — `react-leaflet` `MapContainer` (`preferCanvas`) over a CARTO
  Positron basemap, `/city/grid` as a `GeoJSON` layer with a `lst`/`ndvi`/`hvi`/`built` toggle,
  a hover tooltip per cell, and a click handler opening an MUI `Drawer` with
  `/explain/{cell_id}`'s SHAP drivers.
- Loaded the dataviz skill before choosing any color, since a choropleth is exactly what it's
  scoped for. `src/viz/color.ts`: the sequential-blue ramp (steps 100→700) and the blue↔red
  diverging pair, both copied verbatim from the skill's `references/palette.md` — no
  eyeballed hex values, per its "documented palette only" rule. Sequential blue colors the
  four magnitude layers (one shared ramp, since only one layer renders at a time — no need
  for per-layer hues); the diverging pair colors SHAP driver direction in the explain drawer,
  since that's a polarity question (warming vs cooling), not a magnitude one. Didn't re-run
  the categorical validator script — sequential/diverging ramps are validated by lightness
  monotonicity and by being copied from the documented instance, not by the adjacency-CVD
  checks that script runs (the skill's own note: running it on a sequential ramp fails by
  design and isn't a real failure).
- `SequentialLegend.tsx` — a labeled gradient bar (title, min, max) so the map is never
  color-alone, per the skill's accessibility pass.
- Verified live, backend and frontend both actually running, not just compiled: real ~12k-cell
  grid, a real 29.8–50.6 °C legend range, a real clicked cell's real SHAP drivers, a real NDVI
  layer switch. Zero console errors.

**Decided**
- One shared sequential ramp across all four layers, not four different hues. Only one layer
  is visible at a time (a toggle, not simultaneous layers), so there's no CVD-adjacency
  concern between them — the palette's categorical machinery (fixed hue order, adjacency
  checks) is for when multiple series share a canvas at once, which never happens here.

**Broke / learned**
- First verification attempt looked for `.leaflet-interactive` DOM elements to click — that
  class only exists under Leaflet's *SVG* renderer. `preferCanvas` (used deliberately, per
  the kickoff task's own performance note for ~12k polygons) draws every feature onto one
  `<canvas>` element with no per-shape DOM node at all. Fixed by clicking raw screen
  coordinates instead — Leaflet's canvas renderer does its own hit-testing internally, so a
  coordinate click still resolves to the right feature and fires the bound handlers; there's
  just nothing to `querySelector` for it.
- The layer-toggle `ToggleButtonGroup` and Leaflet's own zoom control both default to
  top-left — found genuinely overlapping in the first screenshot (LST button partly hidden
  behind the +/− control), not caught by `tsc` or lint since it's a pure layout collision.
  Fixed by offsetting the toggle group's `left` past the zoom control's width; re-screenshot
  confirmed the fix.

**Next**
- Analytics: `/hotspots` ranking (table + Recharts bar chart — the dataviz skill's ordinal
  and sequential guidance applies again), `/weather` widget, `/trends`' honest stub state.

---

## 2026-07-27 — Phase 5 — Scaffold & plumbing

**Done**
- `frontend/`: `npm create vite@latest . -- --template react-ts`, then the real stack on top
  (MUI, react-leaflet + leaflet, Recharts, `@tanstack/react-query`). React 19.2, TS 6.0, Vite
  8.1 — current as of this scaffold.
- `src/api/types.ts` + `client.ts` + `hooks.ts` — hand-written types mirroring
  `backend/schemas.py`, one `fetch` function and one TanStack Query hook per client-facing
  endpoint.
- `src/App.tsx` + `main.tsx` — the MUI `AppBar`/`Tabs` shell, `QueryClientProvider` with
  `refetchOnWindowFocus: false`, five `Placeholder` sections.
- Verified live: dev server up, Playwright-driven headless Chromium (no `chromium-cli` on
  this Windows box — installed `playwright` locally with `--no-save`, used it, removed it;
  `package.json`/`package-lock.json` confirmed untouched by the temporary install) navigated
  the app, clicked all 5 tabs, screenshotted each, checked `console --errors`. Clean.

**Decided**
- `strict: true` wasn't in the fresh Vite scaffold's `tsconfig.app.json` — a real gap against
  `conventions.md`'s explicit requirement, not a style preference. Added it before writing
  anything else, and confirmed `npx tsc -b` actually enforces it (not just present in the
  file — ran it before and after to see the difference).
- Deleted the scaffold's default `App.css`/hero-and-logo assets and rewrote `index.css`. The
  default template is a centered 1126px-wide marketing column (`#root { width: 1126px; ...
  text-align: center; }`) — directly incompatible with a full-height `AppBar` + content
  dashboard layout. Left in place, it would have silently constrained every section to a
  narrow centered column no matter what the section components did.
- `frontend/README.md` rewritten from Vite's generic template boilerplate — pointed at the
  actual backend dependency, env var, and the three kickoff decisions baked into `src/api/`.

**Broke / learned**
- First draft of `client.ts` included `cellStats` and `explainWard` functions calling
  `/cell/{id}/stats` and `/explain-ward/{code}` — endpoints that don't exist.
  `get_cell_stats` and `explain_ward` (`backend/agents/tools.py`) were built as agent-toolbelt
  functions only, never given their own HTTP routes (Phase 4 never needed them as REST
  endpoints, only as LLM tool calls). Caught by grepping `backend/routers/*.py` for every
  actual `@router.get`/`@router.post` before trusting what I'd written from memory — 11 real
  routes, not 13. Removed both functions and their now-orphaned types
  (`CellStatsResponse`/`WardExplainResponse`) from `types.ts` rather than leaving dead code
  that implies a capability the backend doesn't have.
- `@types/geojson`'s global `GeoJSON` namespace didn't resolve at first —
  `tsconfig.app.json`'s `"types": ["vite/client"]` explicitly lists which `@types/*` packages
  auto-include, which suppresses the normal automatic pickup of every installed `@types/*`
  package. Added `"geojson"` to that list once diagnosed (`@types/geojson` was already present
  transitively via `@types/leaflet`, just not wired in).

**Next**
- Heat map: `react-leaflet` + `/city/grid` GeoJSON layer, canvas renderer, layer toggle,
  click-to-explain via `/explain/{cell_id}`.

---

## 2026-07-27 — Phase 5 — Kickoff: React dashboard planning pass

**Done**
- Planning pass before code, per `BLUEPRINT.md` §8. `BLUEPRINT.md`'s stack map already locks
  React + TS + Vite + MUI + react-leaflet + Recharts, so the kickoff questions were about
  implementation patterns within that stack, not the stack itself. Expanded PROGRESS.md's
  Phase 5 board into scaffold/map/analytics/scenario/chat/alerts groups.

**Decided (author-confirmed, all four recommended)**
- **TanStack Query**, not plain `fetch`+`useState` — declarative caching matters more than
  usual here, since `/agent/chat` is slow and quota-limited (20 req/day, measured in Phase 4)
  and an accidental refetch is a real cost, not just wasted latency.
- **Hand-written TypeScript types**, not generated from `/openapi.json` — matches
  `conventions.md`'s literal wording ("API response types mirror the backend Pydantic
  schemas") and avoids a codegen dependency for a backend that's still evolving.
- **Single page, section switcher, no router** — five sections on one internal dashboard, no
  need for shareable per-section URLs.
- **Manual/visual verification is the Definition of Done** — no Vitest/RTL suite this phase;
  every feature clicked through in a running dev server, matching the standing UI-work
  instruction rather than adding a parallel test framework to maintain.
- No new ADR: these are patterns within an already-locked stack, not new architectural
  commitments with long-term consequences — matches Phase 3's kickoff precedent (no ADR),
  not Phase 2/4's (ADR-0008/0009, genuine scope/methodology decisions).

**Next**
- Scaffold & plumbing: `npm create vite@latest`, the API client, hand-written types, TanStack
  Query setup, the app shell — the board's first unchecked group.

---

## 2026-07-27 — Phase 4 — Close-out

**Done**
- Author confirmed the exit criterion and ticked it: ✅ *Copilot answers a real planning
  question with real model numbers* — the live verification earlier this session (real Ward L
  numbers, real SHAP drivers, real citations, no fabricated cost) is what's being confirmed
  here, not a fresh check.
- `docs/CHANGELOG.md` gets the Phase 4 entry: the toolbelt/services split, RAG over 3 real
  documents, the four agents, the supervisor + cache, alert dedupe, three new endpoints, three
  new ADRs (0009–0011), 122 tests. Known limitations carried forward listed plainly — no Groq
  fallback, Monitoring's threshold-only rule, no chat memory, the cron's inert state, the RAG
  MVP subset, no cost axis on Planning's recommendations.
- `docs/architecture.md` updated to reality: LangGraph orchestration and the agent
  tools/services layer are ✅ in the Components diagram (Report generation stays ⬜, Phase 7);
  the deployment diagram's GitHub Actions node is 🟨 (built, inert until `BACKEND_URL`
  exists); the Groq-fallback bullet in the free-tier realities list corrected to match
  ADR-0011 and the real measured 20 req/day quota.
- `PROGRESS.md` rolled to Phase 5.

**Next**
- Phase 5 kickoff: React dashboard over what Phases 3–4 already serve (map, analytics,
  scenario simulator, Copilot chat, alerts feed) — a planning pass before code, per
  `BLUEPRINT.md` §8, same as every prior phase kickoff.

---

## 2026-07-27 — Phase 4 — Monitoring cron: dedupe, two endpoints, the GH Actions trigger

**Done**
- `backend/agents/alerts.py` — the dedupe + persistence layer `agents.md` §7 calls for
  ("one alert per event, not per run"). File-based (ADR-0004): `alerts_state.json` tracks
  yesterday's severity, `alerts.jsonl` is an append-only log of new/escalated alerts.
  `check_and_log()` compares today's severity against the stored state — a fresh trigger
  (state was "none") or an escalation (severity increased) gets logged; the same or a lower
  severity continuing does not; a no-trigger day resets the state so the *next* trigger reads
  as fresh, not a continuation.
- `monitoring.py`'s `_draft_summary` now falls back to a fixed-template summary if the LLM is
  unavailable (`RuntimeError` from `get_llm()` with no key, or `ChatGoogleGenerativeAIError`
  from a real call failing) — the trigger is deterministic and real either way; only the prose
  quality degrades. Worth doing given this exact project's LLM credential has broken twice
  already this session.
- Two endpoints: `POST /monitoring/check` (`backend/routers/monitoring.py`) — the HTTP trigger
  point `architecture.md` §6 always specified (GitHub Actions → trigger → Render), runs
  `check_and_log` against `app.state.store` directly, independent of `app.state.supervisor`
  (Monitoring doesn't need the RAG index or chat agents). `GET /alerts`
  (`backend/routers/alerts.py`) — reads the log back, the contract `api-reference.md` already
  sketched.
- `.github/workflows/monitoring.yml` — `30 0 * * *` (00:30 UTC = 06:00 IST). Calls
  `$BACKEND_URL/monitoring/check`, nothing more — no pipeline rebuild in CI, which would need
  Earth Engine credentials and quota in a scheduled job (exactly what
  `architecture.md`'s "pipeline runs are deliberate, not on a loop" was written to prevent).
  Exits 0 with a message when `BACKEND_URL` isn't set, which it won't be until Phase 6 deploys
  — an honest no-op, not a nightly red cross for a URL that doesn't exist yet.
- `tests/test_monitoring_cron.py` — 10 tests. The dedupe matrix run as a real sequence of
  `check_and_log` calls (new event → continuing → escalation → de-escalation → gap → fresh
  event again), each step's log state asserted, not just the final one. Both endpoints tested
  through the real app via `TestClient`. Everything against `tmp_path` — confirmed the real
  `data/processed/alerts_state.json` this session's manual smoke-testing created earlier is
  untouched by the suite.

**Decided**
- The router-level trigger endpoint recomputes "today" from `datetime.now()` rather than
  reading it back from the just-written log — an early draft read the log's last entry for
  the date, which is wrong on a *continuing* (deduped) day: the log's most recent entry is
  from the event's onset, not today. Caught before writing tests, not after.
- Dedupe compares severity, not just "triggered or not" — an escalation from advisory to
  severe heat wave mid-event is genuinely new information worth its own alert, even though the
  underlying "event" (in the loose sense) never fully stopped.

**Next**
- Phase 4 exit: ✅ *Copilot answers a real planning question with real model numbers* — the
  live verification two entries back already demonstrated this (Ward L, real SHAP drivers,
  real citations). Author to confirm and tick, per convention — not done here.

---

## 2026-07-27 — Phase 4 — Rate-limit hygiene: cache, explicit backoff, dropped Groq

**Done**
- **ADR-0011: dropped the Groq fallback**, author's call, asked directly. One credential to
  manage instead of two; the response cache below covers the practical scenario (repeat demo
  questions) the fallback mainly protected against. `GROQ_API_KEY` stays scaffolded and unused
  in `.env.example` — cheap to pick back up later if a future phase needs the uptime.
- **Response cache**: `Supervisor` now owns a `TTLCache` keyed on `(question.strip(),
  data_version)`, 24h TTL. Lives inside `Supervisor.handle()`, not the router — any future
  caller of the supervisor gets the caching for free, and `data_version` (already on `Store`)
  means the cache doesn't need its own invalidation logic; it just naturally misses once the
  pipeline re-runs. A failed call is never cached — confirmed by test, not just by reading
  `TTLCache.get_or_set`'s source (the store-write happens after `compute()` returns, so an
  exception propagates before it).
- **Backoff made explicit**: `ChatGoogleGenerativeAI` already retries with exponential backoff
  internally — no code needed there, confirmed live in the last entry (1s/2s/4s/8s observed).
  Set `max_retries=3` explicitly in `get_llm()` instead of leaving it at the library's default
  of 6: on a real quota exhaustion (not a transient blip), 6 retries means 30+ seconds before
  `/agent/chat` responds, which is worse than a fast, honest 503.
- `docs/agents.md` §8's rate-limit table rewritten with a Status column — cache ✅, backoff ✅,
  fallback ❌ dropped (ADR-0011) — so the table describes what's built, not the original plan.
- `runbook.md` §5's pre-demo checklist rewritten with the real 20/day number (not ~1,500) and
  a caveat the old wording didn't have: the cache is an **exact string match**, so a rephrased
  question at demo time is a genuine miss, not a hit. Also flagged that there is no fallback
  provider to lean on if the quota exhausts mid-demo.
- `tests/test_orchestration.py` — 5 new tests: identical-question cache hit (via scripted-
  response exhaustion — a real miss would raise `IndexError` popping a third response that
  isn't there, so the test fails loudly rather than silently passing on a miss), a reworded
  question missing the cache, a failed call not poisoning it, and `get_llm()`'s explicit
  `max_retries`. All tests still green (mock suite unaffected by the live key working now);
  full suite confirmed passing.

**Decided**
- Cache lives in `Supervisor`, not `backend/routers/agent.py` — same reasoning as
  `build_agent_layer` staying out of `services.py` (ADR-0009's "two interfaces" rule is about
  the toolbelt/HTTP duality specifically), but the opposite conclusion: the cache genuinely
  belongs with the thing being cached (a chat interaction), not the one caller that happens to
  exist today.
- Cache key is a strict string match, deliberately not fuzzy/semantic. `agents.md` §8's
  original design just says "hash (question + data version)" — matching that literally is
  simpler to explain and test than adding a similarity threshold, and the runbook already
  routes around the limitation (warm with the *exact* scripted wording).

**Next**
- Monitoring cron: `.github/workflows/` daily trigger, alert dedupe, file output.

---

## 2026-07-27 — Phase 4 — Live LLM verification: the key, and two real bugs it found

**Done — the key**
- Regenerated `GEMINI_API_KEY` twice from the same AI Studio project: identical `403
  PERMISSION_DENIED: Your project has been denied access` both times. Pushed back on an
  AI-generated explanation the author found ("Google changed key formats to `AQ.`, old SDKs
  reject it") — the traceback shows the request reaching Google's servers and getting a real,
  structured JSON error back (`google/genai/_api_client.py`'s `raise_for_response`), which
  only happens *after* the key is accepted and parsed; a format-rejection would fail
  client-side before any network call. Also: `google-genai` was already at the latest
  release (2.14.0, confirmed via `uv pip install --dry-run`), so "outdated SDK" didn't hold
  either.
- A key from a genuinely **different Google account** worked on the first try, no code
  changes. Confirms the diagnosis: project-level denial, not a key-format or SDK issue.
  `runbook.md` and `PROGRESS.md` updated so the record reflects what was actually verified,
  not the AI-search theory.

**Done — live verification, all four agents + the supervisor**
- **Copilot**: "Which ward is hottest and why?" → `get_hotspots` then `explain_ward`, real
  numbers (Ward L, 43.18 °C, +3.22 °C over city mean), correctly labelled *surface*
  temperature, SHAP drivers cited with values and units.
- **Planning**: "What should we do about ward L?" → `explain_ward`, `get_hotspots`, then
  `simulate_scenario` for *both* `cool_roof` and `greening`, ranked by ΔLST × population,
  zero mention of cost anywhere in the answer — ADR-0009's descope holding under a real model,
  not just enforced by the system prompt's wording.
- **Digital Twin**: "What if we plant trees across 30% of ward A?" → correctly explained that
  greening doesn't take a coverage fraction (rather than silently applying 30% somewhere it
  doesn't apply), ran the scenario, phrased the result as "cells like these... run cooler" —
  analogy, not a promise — and disclosed `clamped: false` explicitly.
- **Monitoring**: real forecast check → no trigger (expected — Mumbai rarely hits 45 °C,
  ADR-0010's own stated consequence). Forced the wording-draft path directly: correct
  severity, correct wards, ends with "not an official IMD warning" unprompted beyond what the
  prompt already asks for.
- **Supervisor.route**: three test messages ("where/why hot", "what should we do", "what
  if... cool-roof") routed to `copilot`/`planning`/`digital_twin` respectively — all three
  correct.

**Broke / learned — two real bugs, found only by going live**
- `AIMessage.content` from real Gemini responses is a **list of content blocks**
  (`[{"type": "text", "text": "...", "extras": {"signature": "..."}}]`), not a plain string.
  Every mock test used `AIMessage(content="plain string")`, so 94 passing tests never
  exercised this shape. Two places assumed `str`:
  - `result.py`'s final-answer extraction — would have handed `AgentChatResponse`'s
    `text: str` field a Python list-repr string like `"[{'type': 'text', ...}]"` instead of
    the actual answer.
  - `monitoring.py`'s `_draft_summary` — same failure, would have produced an unreadable
    alert.
  - **The more serious one**: `supervisor.py`'s `route()` did `str(response.content)` then
    compared it to `"copilot"`/`"planning"`/`"digital_twin"`. A stringified block list never
    equals any of those, so this would have **silently routed every single message to the
    `copilot` fallback**, permanently, with no error and no test catching it — the fallback
    path was specifically designed to look like a reasonable default, which is exactly what
    made it dangerous here.
  - Fix, all three: `BaseMessage.text` (a `TextAccessor` that normalizes either `str` or
    `list[dict]` content) instead of `.content`, wrapped in `str()`. Verified live after the
    fix: real routing now correctly discriminates all three agents.
  - `ToolMessage.content` (used in `result.py`'s tool-call recording) does **not** have this
    problem — it comes from our own `StructuredTool`/`ToolNode` JSON-serializing a dict
    return, a different code path from the model's own response, confirmed still a plain
    JSON string.
- Hit a real `429 RESOURCE_EXHAUSTED` after enough live calls in one session — and the
  `agent_upstream_unavailable` handling (`backend/routers/agent.py`) worked exactly as
  designed: clean `503`, real error text, no crash. The quota error itself was informative:
  Google named the limit explicitly — `generate_content_free_tier_requests`,
  `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, `quotaValue: 20` — **20 requests/day**
  for `gemini-flash-latest` (currently aliased to `gemini-3.6-flash`), not the ~1,500/day
  `BLUEPRINT.md` documented. Corrected there with a dated note (may be a new-project quota,
  not universal — noted as such). Sharpens the case for the next task: 20/day means caching
  matters even for a modest demo, not just for burst traffic.

**Next**
- Rate-limit hygiene: response cache keyed on (question, `data_version`) is now clearly not
  optional — 20 req/day is tight. Backoff is already handled inside `google-genai`'s own
  client (observed live: 1s/2s/4s/8s/16s retries before our code ever sees the error), so that
  part of ADR-0002's plan may already be satisfied without extra code; Groq fallback still
  needs `GROQ_API_KEY` set, which it currently isn't.

---

## 2026-07-27 — Phase 4 — Orchestration: supervisor + `POST /agent/chat`

**Done**
- `backend/agents/supervisor.py` — `Supervisor`, built once per app lifetime like `Store`
  (ADR-0004's posture applied to the agent layer). `route()` is a plain one-word
  classification (`copilot`/`planning`/`digital_twin`), parsed and validated in Python rather
  than `BaseChatModel.with_structured_output()` — its default implementation routes through
  `bind_tools()` and a provider-specific tool-calling flow, a layer of indirection this simple
  a decision doesn't need. An unparseable reply falls back to `copilot` (the general-purpose
  agent), not a guess at intent. `handle()` routes then dispatches to the chosen agent's own
  `run_agent()` loop — one router LLM call, then up to `MAX_TOOL_CALLS` more inside whichever
  agent handles it, matching `agents.md` §2's "single classification call, not a negotiation."
- `build_agent_layer()` (same module — orchestration-only logic, not a `services.py` function,
  since nothing else calls it): if the dispatched agent called `simulate_scenario`, builds a
  `/city/grid`-shaped GeoJSON FeatureCollection scoped to just those cells; any other tool
  call, or none, returns `None` — an unmappable answer stays unmappable, not padded with an
  invented layer.
- `backend/routers/agent.py` — `POST /agent/chat`. Two distinct 503s: `agent_layer_unavailable`
  when `app.state.supervisor` is `None` (RAG index or `GEMINI_API_KEY` missing entirely, set at
  startup) vs. `agent_upstream_unavailable` when a *present* key fails at call time
  (`ChatGoogleGenerativeAIError` caught around `supervisor.handle()`) — construction alone
  doesn't spend a real call to validate a key, so a broken-but-present key can only be caught
  here, not at startup.
- `main.py`'s `lifespan` now also builds `app.state.retriever` and `app.state.supervisor`,
  both optional: wrapped in `try/except FileNotFoundError`/`RuntimeError` so a fresh clone (no
  RAG index) or a missing key degrades to `/agent/chat` 503ing, not the whole app failing to
  start. App version bumped to 0.4.0.
- `tests/test_orchestration.py` — 13 tests: routing + the fallback (parametrized over five
  raw responses), `handle()` dispatching and surfacing tool calls, `build_agent_layer` against
  a *real* `simulate_scenario` result (not a stub), and the endpoint's three response shapes
  (200, both 503s) via `TestClient` with a stand-in supervisor.
- **Fixture cleanup while here**: `store` and `retriever` had become duplicated, function-
  scoped fixtures across `test_agents.py`, `test_rag.py`, and now `test_orchestration.py` —
  each test was reloading the feature table and the sentence-transformers embedding model
  from scratch. Moved both to `tests/conftest.py`, session-scoped, matching the
  `settings`/`features`/`wards_gdf` fixtures already there. Full suite is noticeably faster;
  now 107 tests, green; `ruff` clean.

**Decided**
- Router logic lives with `Supervisor` in `backend/agents/supervisor.py`, not `services.py`.
  `services.py` is specifically the "one implementation, two interfaces" layer the HTTP routes
  and the agent toolbelt both call (ADR-0009) — `build_agent_layer` has exactly one caller
  (`/agent/chat`), so putting it in `services.py` would misrepresent it as more reusable than
  it is.
- Plain-text routing over `with_structured_output`: fewer moving parts to explain,
  and this project's own fake-model test harness (`FakeToolCallingModel`) already proved that
  `with_structured_output`'s default tool-calling path needs more scripting to fake correctly
  — a sign it's more machinery than a one-of-three classification needs.

**Broke / learned — the "new key" attempt, and what it actually told us**
- Author generated a fresh `GEMINI_API_KEY` from AI Studio and swapped it into `.env`. Same
  live test, same result: `403 PERMISSION_DENIED: Your project has been denied access.`
  **Same error text as the first key** — that's the useful signal. A stale/expired key
  produces a *different* error (usually `INVALID_ARGUMENT` or `UNAUTHENTICATED`); getting the
  identical `PERMISSION_DENIED` from a brand-new key means the denial is scoped to the AI
  Studio *project*, not the key. Documented in `runbook.md` and `PROGRESS.md`: the fix is a
  key from a *new* project, not another key from this one.
- This is exactly why `main.py`'s startup check only catches *absence* (no key at all), not
  *validity* — validating a key would mean spending a real call on every restart, and the
  fresh-key test above shows validity can change out from under a previously-passing key
  anyway. The request-time 503 (`agent_upstream_unavailable`) is the layer that actually needs
  to carry this, and now does.

**Next**
- Rate-limit hygiene: response cache keyed on (question, `data_version`), 429 backoff, Groq
  fallback. Doesn't need a working Gemini key to build — the cache and backoff logic wrap
  `Supervisor.handle()` regardless of whether the call underneath succeeds.

---

## 2026-07-27 — Phase 4 — The four agents: built, tested, live verification blocked

**Done**
- `backend/agents/llm.py` — `get_llm()`, one place reading `GEMINI_API_KEY` (ADR-0002). No
  retry/backoff/Groq-fallback here on purpose — that's the next task group, Rate-limit hygiene.
- `backend/agents/prompts.py` — plain-text system prompts for Copilot, Planning, Digital Twin,
  carrying the guardrail language from `agents.md` §4–§6 (measurement caveats, no-invented-
  numbers, ask-don't-guess, clamped-must-be-disclosed).
- `backend/agents/result.py` — `AgentResult`/`ToolCallRecord` + `run_agent()`: invokes a
  compiled LangGraph agent, flattens its message trace into final text + the tool calls made
  (the transparency `POST /agent/chat` will need later), bounded to `MAX_TOOL_CALLS=4` via
  `recursion_limit` (agents.md §8's "bounded tool-call loop"). Catches `GraphRecursionError`
  and returns an honest "ran out of budget" message instead of letting a runaway loop hang or
  crash the request.
- Three tool-calling agents via `langchain.agents.create_agent` (the current, non-deprecated
  API — `langgraph.prebuilt.create_react_agent` is deprecated as of langgraph 1.x, moved
  there): `copilot.py` (every toolbelt tool except `simulate_scenario`, requires a real
  `Retriever` — no silent RAG-less Copilot), `planning.py` (`get_hotspots`, `explain_ward`,
  `simulate_scenario`), `digital_twin.py` (`simulate_scenario`, `get_cell_stats`,
  `explain_ward`).
- `monitoring.py` — deliberately *not* a tool-calling agent (agents.md §7: the trigger is
  deterministic code, the LLM only drafts wording). `check_heatwave()` calls
  `services.get_weather` and `services.hotspots` directly, applies `_severity()`, and only
  calls the LLM if a trigger actually fired.
- `tests/test_agents.py` — 16 tests. Built a small local `FakeToolCallingModel`
  (`BaseChatModel` subclass, `bind_tools` returns `self`, `_generate` pops a scripted
  response) since none of `langchain_core`'s built-in fakes implement `bind_tools`. Runs the
  *real* tool-calling loop against *real* tools and the *real* store — only the model is
  fake — so `run_agent`'s extraction, each agent's tool membership, tool-error-as-labelled-
  result, and the recursion-limit catch are all genuinely exercised, not just asserted.
- 94 tests total, green; `ruff` clean.

**Decided**
- **ADR-0010: Monitoring's heat-wave rule is absolute-threshold-only** (37/45/47 °C from the
  IMD FAQ, `data/knowledge_base/imd_faq_heatwave.txt`), not IMD's full coastal-station rule.
  IMD's real rule needs a departure from the station's climatological normal maximum
  temperature; this project's only candidate baseline is Phase 1's ERA5 dry-season *mean* air
  temperature, already found near-constant across the city and flagged as low-signal — using
  it as an IMD "normal" would misrepresent both what IMD's criteria mean and what the data
  supports. Author-confirmed via AskUserQuestion before building. Consequence, stated plainly
  in the ADR: the agent will rarely trigger for Mumbai in practice (45 °C+ is uncommon at a
  coastal station) — a live demo may need a mocked forecast to show the alert path.
- **`create_agent`, not `create_react_agent`.** Tried the latter first per older tutorials;
  langgraph 1.2.9 raises a deprecation warning and points at `langchain.agents.create_agent`,
  which is what actually ships now.
- **Fake-model test ids must be unique per turn.** First draft of the runaway-loop test reused
  one `tool_call` id across every scripted response — langgraph's internal routing threw a
  `KeyError` on the *n*th repeat (an artifact of an internal branch spec, not a real bug in
  our code — a real model never emits the same id twice). Fixed by generating a unique id per
  turn in the test, which is also more realistic.

**Broke / learned — the live LLM check surfaced a real, external blocker**
- `GEMINI_API_KEY` fails every real call with `403 PERMISSION_DENIED: Your project has been
  denied access. Please contact support.` — not a rate limit. The key also doesn't match a
  valid AI Studio key's shape (`AIzaSy...`); this one starts `AQ.Ab8R...`, suggesting the
  wrong credential was pasted into `.env`, not that a real key expired. `GROQ_API_KEY` is
  unset, so there is currently no working LLM credential in this environment at all.
- Author-confirmed path forward (AskUserQuestion, before building): build all four agents now
  with mock-tested wiring, fix the credential separately, then run one real smoke test per
  agent. `runbook.md`'s troubleshooting table now has this exact error + fix + a pointer back
  to this entry, so future-me doesn't have to rediscover it.

**Next**
- Once `GEMINI_API_KEY` (or `GROQ_API_KEY`) works: one live call per agent to confirm real
  behavior, then tick PROGRESS's "Blocked: live LLM verification" line. Otherwise, Orchestration
  — the LangGraph supervisor and `POST /agent/chat` — can proceed on the mock-tested agents as
  they stand; the supervisor's own routing logic doesn't need a working key to build or test.

---

## 2026-07-27 — Phase 4 — RAG knowledge base: real documents, Chroma index, 8th tool

**Done**
- Collected the 3 MVP documents (ADR-0009) with real fetches, not placeholders. MCAP's
  "Summary for Policymakers" PDF and IMD's "FAQ on Heat Wave" PDF both had genuine text
  layers — extracted directly with `pypdf` (12 and 16 pages). NDMA's own detailed guideline
  PDF (`nidm.gov.in/PDF/pubs/NDMA/27.pdf`, 62 pages) turned out to be a scan with **zero**
  extractable characters (verified, no OCR available here) — substituted NDMA's own official
  heat-wave hazard page instead, same authority, real machine-readable content. Logged as a
  limitation in `references.md` §4, not silently swapped.
- The IMD FAQ gave primary-source precision on the exact criteria `agents.md` §7's Monitoring
  agent will need: 40 °C (plains) / 30 °C (hilly) base threshold before a heat wave is even
  considered; Heat Wave = 4.5–6.4 °C departure from normal, Severe = >6.4 °C; by absolute
  temperature, ≥45 °C / ≥47 °C; coastal stations need departure ≥4.5 °C **and** actual max
  ≥37 °C; declared at ≥2 stations in a met sub-division for 2 consecutive days. The MCAP PDF's
  own Urban Heat Risk section independently corroborates this project's HVI ranking: M/E ward
  is its named most heat-vulnerable ward, over 40% of its population exposed to surface
  temperature >35 °C.
- `data/knowledge_base/sources.json` — a small manifest (title, org, url, accessed date,
  paginated flag, notes) so `ingest.py` attaches real per-chunk provenance instead of a bare
  filename.
- `backend/rag/ingest.py`: page-marker-aware chunking (`--- page N ---`, added when the source
  PDF was extracted) at ~800 words / 100 overlap — a word-count proxy for tokens, not exact
  BPE, one fewer moving part to defend. Embeds with `sentence-transformers/all-MiniLM-L6-v2`
  (CPU) into a persisted Chroma collection at `CHROMA_DIR`. `uv run python -m backend.rag.ingest`
  → 28 chunks from the 3 sources.
- `backend/rag/retrieve.py`: `Retriever` loads the model + opens the collection once;
  `.search(query, k)` is cheap after that. Raises `FileNotFoundError` if the index hasn't been
  built — a missing index is a setup problem, not a silent empty-result answer.
- `search_knowledge` wired into `backend/agents/tools.py` — the 8th and final toolbelt entry
  from `agents.md` §3. `build_toolbelt(store, retriever=None)`: a fresh clone that hasn't run
  `ingest.py` yet still gets the other 7 tools rather than failing outright.
- `tests/test_rag.py` — 11 tests: pure-logic chunking (4, always run), real-fixture tests for
  `load_chunks`/`Retriever`/`search_knowledge`/`build_toolbelt` (7, skip cleanly if the
  knowledge base or index isn't built). Manually verified retrieval quality before writing
  tests: querying "what temperature threshold declares a heat wave" surfaced the IMD FAQ
  passage top-3. 78 tests total, green; `ruff` clean.
- Added `pypdf` to `pyproject.toml` — needed for this collection pass and for any future
  document the RAG corpus grows to include (WHO/IPCC/other cities' plans, ADR-0009's deferred
  list).

**Decided**
- **Word-count chunking, not exact tokenization.** Loading a second tokenizer just to size
  chunks precisely would be one more moving part for no retrieval-quality gain at this corpus
  size (28 chunks) — `docs/conventions.md`'s "boring, explainable tech."
- **A scanned-PDF substitution gets logged, not hidden.** The NDMA guideline PDF being
  unreadable is exactly the kind of thing that would look like silent scope-narrowing if not
  written down — `references.md` §4 states plainly what was swapped and why, with the
  verification method (`pypdf`, 0 chars, no OCR available).

**Next**
- Agents: wire the toolbelt + retriever into the four LangGraph agents (`agents.md` §4–§7),
  per the PROGRESS board.

---

## 2026-07-27 — Phase 4 — Shared toolbelt: 7 in-process LangChain tools

**Done**
- New `backend/services.py`: the actual logic for `hotspots`, `explain_cell`, `predict`,
  `scenario`, `get_weather`, `get_trend` moved out of the route handlers (which took a FastAPI
  `Request` and couldn't be called without one) into plain functions taking a `Store`. The six
  routers are now thin — pull `store` off `request.app.state.store`, call `services.xxx(...)`,
  return it. Behavior unchanged: all 17 existing backend tests pass unmodified except one
  monkeypatch target (`backend.routers.weather._fetch` → `backend.services._fetch_weather`,
  since the fetch/cache logic moved too).
- Two new, genuinely new (not extracted) functions in `services.py`: `cell_stats` (a cell's raw
  model-input feature vector — distinct from `explain_cell`'s SHAP attribution) and
  `explain_ward` (aggregated SHAP + summary stats for a whole ward, mean |SHAP| per feature
  across the ward's cells). Two matching schemas: `CellStatsResponse` and `WardExplainResponse`
  with a new `WardDriver` (kept separate from the per-cell `Driver` — its docstring says "for
  this cell", which would be wrong for a ward mean).
- `backend/agents/tools.py`: `build_toolbelt(store) -> list[StructuredTool]`, one
  `StructuredTool.from_function` per tool with an explicit Pydantic `args_schema` (`agents.md`
  §3's "Pydantic validates them", made concrete). 7 of the 8 toolbelt entries from `agents.md`
  §3 — `search_knowledge` needs the Chroma index the RAG task group builds next.
- `tests/test_agent_tools.py` — 12 tests, `.invoke({...})` against real fixtures, no HTTP
  layer, same skip-on-fresh-clone pattern as `test_backend.py`. 67 tests total, green;
  `ruff` clean.

**Decided**
- **Errors come back as a labelled dict, not a raised exception.** Every `services.py`
  function still raises `HTTPException` (via `api_error`) on a domain error — routers need
  that for FastAPI's status codes. But a LangChain tool that raises looks like a crash to the
  agent loop, so each tool wraps its `services` call and turns `HTTPException` into
  `{"error": ..., "error_code": ...}`. Verified: `get_cell_stats(999999999999)` returns
  `error_code="cell_not_found"` rather than raising (`agents.md` §1 — "fail loudly, never
  plausibly" means a legible failure, not a Python traceback).
- **`simulate_scenario` is ward-only.** `agents.md` §3's draft signature sketched
  `ward: str | cell_ids: list`; only ward-level scenarios exist anywhere in the ML layer
  (`ml/scenario.py`, `/scenario`'s own contract). Building cell-level targeting now would be
  new, untested ML surface, not a wrapper — out of scope for "wrap Phase 3 services."
  Documented in the tool description rather than silently dropped.
- A few tool signatures added an optional parameter beyond `agents.md` §3's draft table
  (`get_hotspots`' `unit`, `explain_cell`/`explain_ward`'s `top`) — all already real parameters
  on the underlying `services.py` functions. `agents.md` §3 calls its own signatures drafts,
  "updated as built"; this is that.

**Broke / learned**
- One test I wrote was wrong, not the code: `explain_ward`'s `deviation` is computed from
  the *unrounded* ward/city means, then rounded — same pattern `explain_cell` already used and
  `test_explain_known_land_cell` already asserts on. My first version of
  `test_explain_ward_known_ward` asserted `deviation == round(lst_mean - city_mean, 2)` using
  the *already-rounded* response fields, which fails at a 0.005 rounding boundary (ward A:
  38.72 − 39.96 → −1.24, but the true deviation rounds to −1.25). Fixed with
  `pytest.approx(..., abs=0.02)` — two independently-rounded floats aren't guaranteed to
  satisfy that identity exactly, so the test shouldn't have demanded it.

**Next**
- RAG knowledge base: collect the 3 MVP documents, `backend/rag/ingest.py`, then
  `search_knowledge` — the eighth tool.

---

## 2026-07-27 — Phase 4 — Dependencies & environment

**Done**
- `uv add langchain langgraph langchain-google-genai langchain-groq chromadb
  sentence-transformers` — resolved and installed (283 packages; `torch` is the heavy one at
  ~116 MiB). `langchain-google-genai` wasn't in the kickoff board's list but is needed for the
  primary Gemini provider (ADR-0002), not just the Groq fallback `langchain-groq` was already
  scoped for — added alongside it.
- `data_pipeline/config.py`'s `Settings` gained `gemini_api_key`, `gemini_model`,
  `groq_api_key`, `groq_model`, `chroma_dir` — all with defaults, so pipeline/backend tests
  keep passing on a fresh clone with no LLM key configured. `chroma_dir` resolved against the
  repo root through the same validator as `data_dir`/`model_dir`.
- Verified: all six new packages import cleanly (`uv run python -c "import langchain, ..."`);
  `ruff` clean; full suite still 55 green — the config change touches nothing route/store code
  already depends on.

**Next**
- Shared toolbelt: the in-process LangChain tool wrappers over `backend.store` /
  `data_pipeline.ml.*` (ADR-0009), per the PROGRESS board.

---

## 2026-07-27 — Phase 4 — Kickoff: agentic core planning pass

**Done**
- Closed out Phase 3 (CHANGELOG, architecture — REST API layer now ✅, PROGRESS → 4).
- Read `agents.md` and `BLUEPRINT.md` §6 against Phase 4's actual starting state and expanded
  the phase into a grouped task board (dependencies, toolbelt, RAG, the four agents,
  orchestration, rate-limit hygiene, monitoring cron).
- Wrote ADR-0009, bundling the three coupled scope decisions below (the same reasoning ADR-0008
  used for Phase 2's coupled choices).

**Decided**
- **Tools wired in-process** (`backend.store` / `data_pipeline.ml.*` imports), not HTTP
  loopback — one process to run for a demo, no re-implementation of the Phase 3 services.
- **RAG corpus is a 3-document MVP**: Mumbai Climate Action Plan, NDMA heat-wave guidelines,
  IMD heat-wave criteria (the last also feeds the Monitoring agent's thresholds). WHO/IPCC/
  other-cities' plans stay candidates in `references.md` §4, not built this phase.
- **Agent 2 drops the cost axis**: ranks by ΔLST × population only. No cited cost-per-area
  figure exists yet — the same gap Phase 3 hit and left `cost` out of `/scenario` for.
  `estimate_cost`/`interventions.yaml` deferred until a real citation is logged.

**Broke / learned**
- Caught a genuine cross-document inconsistency while reading, not something introduced today:
  `architecture.md`'s Components diagram and `agents.md`'s own §2 supervisor diagram numbered
  the agents 1=Planning/2=Digital Twin/3=Monitoring/4=Copilot, while `agents.md`'s own §4–§7
  prose headers and PROGRESS.md's old one-line bullet numbered them 1=Copilot/2=Planning/
  3=Digital Twin/4=Monitoring. Canonicalized on the latter (matches prose + PROGRESS already;
  Copilot is also the agent the exit criterion tests) and fixed both diagrams — including the
  retrieval and notification arrows, which had to move with the renumbering, not just the
  bracket labels.

**Next**
- Dependencies (`langchain`, `langgraph`, `chromadb`, `sentence-transformers`, `langchain-groq`)
  then the shared toolbelt, per the new PROGRESS board.

---

## 2026-07-27 — Phase 3 — Model/scenario endpoints: predict, scenario, trends stub

**Done**
- `GET /predict` — the model's own LST prediction for a cell vs. the observed value. Same
  land-fraction restriction as `/explain` (`cell_not_predictable` 404 below it), since the
  model was never trained on mostly-sea cells.
- `POST /scenario` — wraps `ml/scenario.py`'s `greening_delta`/`cool_roof_delta` directly, no
  reimplementation. Added `greening_clamped_mask()` to `ml/scenario.py` (purely additive, its
  own unit test, existing 37 scenario tests untouched) so the API can honestly report which
  cells needed clamping instead of asserting `clamped` from the outside.
- `GET /trends` — the author-confirmed stub: `{available: false, note: ...}`.
- 7 new backend tests + 1 new `ml/scenario` test (58 total green); `ruff` clean.
- Live-verified magnitudes, not just shapes: `/predict`'s residual (0.13 °C) sits well inside
  the model's ~1.10 °C spatial-CV RMSE; `/scenario` cool-roof at 50% coverage on a fully-built
  cell lands at exactly −1.7 °C — Li et al.'s cited figure, reproduced, not approximated.

**Decided**
- **No `cost` field on `/scenario`**, despite the original api-reference draft sketching one.
  `references.md` has no cited cost-per-area figure for either lever, and "a cost or ΔLST
  figure without a source is a fabrication" (references.md) applies to cost the same as it does
  to cooling coefficients. Left out until a real source is logged — not estimated, not guessed.
- `intervention` is `greening` | `cool_roof` (matching `ml/scenario.py`'s actual two levers),
  not the draft's `tree_planting`. `coverage` only means something for `cool_roof`; greening
  always raises NDVI to a fixed target regardless of it — documented as a real model
  limitation, not silently ignored.
- `/predict` is a transparency endpoint only (one cell, its own stored features) — no supplied
  feature-vector override. That "what-if" role belongs to `/scenario`; giving `/predict` the
  same power would just be two endpoints doing one job.

**Next**
- Phase 3 exit: everything demoable from Swagger `/docs` — author to verify, not me.

---

## 2026-07-27 — Phase 3 — Data-serving endpoints: grid, hotspots, explain, weather

**Done**
- `GET /city/grid` — choropleth GeoJSON (`layer=lst|ndvi|hvi|built`), `bbox` viewport filter
  (400 on malformed input), geometry `simplify`. Verified live: default settings + gzip bring
  the full-city `lst` layer from ~4 MB to ~460 KB.
- `GET /hotspots` — ward or cell ranking by `hvi`/`lst`, each with its top SHAP driver
  (mean |SHAP| per feature for wards, that cell's own SHAP row for cells).
- `GET /explain/{cell_id}` — per-cell SHAP drivers, `city_mean`/`deviation`, the `measurement`
  marker. 404 `cell_not_found` for an unknown id, distinct 404 `cell_not_explained` for a real
  cell below the SHAP training threshold (mostly sea).
- `GET /weather` — Open-Meteo forecast passthrough for a city-representative point, TTL-cached
  (`backend/cache.py`, 30 min) — separate from the pipeline's historical per-cell weather stage.
- `backend/errors.py` + a global exception handler in `main.py`: every error is now a flat
  `{detail, error_code}` body (api-reference.md conventions), not FastAPI's default nested shape.
- 11 new tests (50 total green); `ruff format`/`check` clean.

**Decided**
- `/city/grid` and `/hotspots` return `ward_code`, not `ward_name` — `data-dictionary.md` §grid
  already records that `ward_name` was never populated (BMC source has no name field; an
  official mapping needs a citable source). `api-reference.md` updated to match reality instead
  of carrying the stale placeholder forward.
- `/weather` hits Open-Meteo's *forecast* API for one point, not the pipeline's per-cell
  archive — this endpoint is live dashboard context, not a model feature, and the weather
  stage's own finding (ERA5-scale weather barely varies across 458 km²) means one point suffices.

**Broke / learned**
- Nothing broke; the live smoke test doubled as a correctness check — the top-5 `hotspots`
  ward ranking (`B, L, C, H/E, F/S`) landed exactly on the HVI ranking already measured and
  documented in Phase 2 (`data-dictionary.md`), a good sign the join logic is right, not just
  non-empty.
- Caught before writing tests: the earlier skeleton commit (`899a957`) never got a devlog entry
  — added retroactively below so the record isn't missing that step.

**Next**
- Model/scenario endpoints: `GET /predict`, `POST /scenario` (wrap `ml/scenario.py`, surface
  `clamped`), `GET /trends` stub. Then the Phase 3 exit criterion (author-verified from Swagger).

---

## 2026-07-26 — Phase 3 — Backend skeleton: startup store + `/health`

**Done**
- `backend/` package: FastAPI app with a `lifespan` that loads `features.parquet`, `hvi.parquet`,
  `wards.geojson`, `model.joblib` and `shap_values.parquet` once into `app.state.store`
  (ADR-0004 — files, not a DB). CORS from `CORS_ORIGINS`, gzip middleware ahead of the coming
  GeoJSON payloads (ADR-0003), structured logging.
- `GET /health` → `model_version`, `data_version`, `uptime_s`, `n_cells`. `schemas.py` scaffold
  with the `measurement: land_surface_temperature` marker for later endpoints.
- Added `fastapi`, `uvicorn[standard]` to deps, `httpx` to dev deps (TestClient); `backend`
  added to the hatch wheel packages. `tests/test_backend.py`: boots the real app, skips cleanly
  on a fresh clone if artifacts are missing. 39 green.

**Decided**
- No response caching or rate limiting yet — premature before there's a second endpoint to
  compare against.

**Next**
- Data-serving endpoints on top of the store: `/city/grid`, `/hotspots`, `/explain/{cell_id}`,
  `/weather`.

---

## 2026-07-26 — Phase 3 — Kickoff: FastAPI backend planning pass

**Done**
- Closed out Phase 2 (CHANGELOG, architecture A→H, PROGRESS → 3). Read the `api-reference.md`
  contracts; expanded Phase 3 into grouped tasks.

**Decided**
- **In-memory store, no DB** (ADR-0004): the backend loads `features.parquet`, `hvi.parquet`,
  `wards.geojson`, `model.joblib` and `shap_values.parquet` once at startup (a few MB) and
  serves from memory. No Redis — an in-process TTL cache (ADR-0003).
- **`/trends` stubbed** (author-confirmed): it needs `lst_trend` (per-year slopes), deferred in
  Phase 1. Ship a clear "not yet available" rather than fake data or a detour back through the
  EE pipeline. The other six endpoints all serve real, built artifacts.
- **`/city/grid`**: GeoJSON + gzip + geometry simplification now; vector tiles only if it stays
  heavy (the api-reference bandwidth note). `/agent/chat` and `/alerts` remain Phase 4.

**Next**
- Skeleton first: `backend/` package (FastAPI app, `pydantic-settings`, CORS, structured
  logging), the startup store, `GET /health`. Then the data-serving endpoints on top.

---

## 2026-07-26 — Phase 2 — Scenario engine: the digital twin, honestly

**Done**
- Read and logged the intervention-coefficient literature in `references.md`: Li et al. (2014)
  for cool roofs, Santamouris (2014), Grover & Singh (2015) for NDVI cooling in Indian metros.
- `data_pipeline/ml/scenario.py`: `simulate` = perturb features → clamp to the training
  envelope → re-predict. Greening and cool-roof levers, four tests; 37 green. Demonstration
  greening + cool-roof map → `data/processed/scenario_greening.parquet`.

**Decided — the engine is a hybrid, by necessity**
- **Greening goes through the model** (raise NDVI toward 0.4, re-predict). Defensible because
  SHAP validated NDVI's cooling and Grover & Singh (2015) corroborate ~1.39 °C/unit NDVI.
- **Cool roofs do NOT** — the model's albedo coefficient is the confound (ADR-0008), so raising
  albedo through the model would predict *warming*. ΔLST comes from Li et al. (2014) directly:
  `−(1.7/0.5)·built_fraction·coverage`. This is where a full phase of albedo caution pays off —
  the one lever that would have silently backfired is the one built on a cited coefficient.
- **Every value clamped to the training envelope** — no extrapolation into confident nonsense.

**Broke / learned — greening warmed 482 cells, and how to handle it honestly**
- The raw model cooled 7,410 cells but *warmed* 482 under greening. Cause: raising NDVI while
  holding built/NDBI fixed creates off-manifold combinations (high built *and* high NDVI, rare
  in training) where a correlational tree model is unconstrained and can predict either way.
- **Fix, honestly:** greening cannot warm a cell all-else-equal, so the delivered map floors
  ΔLST at 0 and *reports the floored count* — not hidden. The principled v2 is a
  monotone-constrained model (NDVI forced cooling); the floor is the honest interim. Logged in
  ml-methodology §6.

**Results**
- Greening cools 7,410 cells, mean −0.65 °C, best −4.88 °C, concentrated in the hot dense grey
  wards (B, C, L) — targets exactly where greening helps most. Cool-roof: mean −1.38 °C, best
  −3.40 °C over built cells.

**Next**
- Phase 2 ✅ ready for the author to verify (a sensible greening ΔLST map). Then phase-close and
  Phase 3 (the FastAPI backend over the model, HVI and scenarios).

---

## 2026-07-26 — Phase 2 — Heat Vulnerability Index + ward hotspot ranking

**Done**
- `data_pipeline/ml/hvi.py`: HVI = 0.4·norm(lst) + 0.4·norm(pop_density) + 0.2·norm(1−ndvi),
  min–max over land cells → `data/processed/hvi.parquet` (per-cell `hvi`, the three components,
  `hotspot_rank`). Ward ranking + the mandatory sensitivity analysis. Four tests; 34 green.

**Decided**
- **HVI lives in its own `hvi.parquet`, not `features.parquet`.** It is derived from `lst_mean`
  (the model's target), so putting it in the feature table would invite leakage. Kept separate,
  keyed on `cell_id`. Updated the data-dictionary accordingly.
- **Weights 0.4/0.4/0.2** (ml-methodology §5) — kept as a parameter of `compute_hvi`, so the
  Phase 3 API can expose re-weighting.

**Results — the index is robust, which is the whole point**
- Most-vulnerable wards: B, L, C, H/E, F/S, K/E, G/N (Dharavi), E — the dense, hot wards, and
  they match the "hot AND dense" cells Phase 1 flagged. The HVI is doing what it should:
  surfacing where heat *and* people coincide, not just the hottest empty ground.
- **Sensitivity check passes decisively** — across five weight variants the top-10 ward ranking
  holds at 9–10/10 overlap, Spearman ρ ≥ 0.98. ml-methodology §5 made this the go/no-go gate
  (fragile ranking = don't publish); the ranking does not flip, so it ships.

**Next**
- Scenario engine v1 — `simulate(feature_deltas) → ΔLST`, clamped to the training envelope, with
  the cool-roof lever using a **cited** albedo coefficient (not the model's confounded one). The
  intervention coefficients need the UHI papers read and logged in `references.md` first.

---

## 2026-07-26 — Phase 2 — SHAP, and the physics gate earns its keep

**Done**
- `data_pipeline/ml/explain.py`: SHAP TreeExplainer on the saved XGBoost — global mean|SHAP|,
  per-cell attribution (→ `models/shap_values.parquet` for `/explain/{cell_id}`), and the
  physics gate. `shap` added. Four gate tests; 30 total green.

**Results**
- Top drivers: `ndbi_mean` 1.41 °C, `albedo` 0.51, `pop_density` 0.37, `built_fraction` 0.36,
  `ndvi_neigh_mean` 0.33, `dist_coast` 0.29 — built-up, vegetation and coast, as expected.
- **`albedo` came out warm — the confound, exactly as ADR-0008 predicted.** The Phase 1
  groundwork made this a *note*, not a scare: the gate already knew to expect it.

**Broke / learned — the gate fired, and fixing it was the real finding**
- First run the gate FAILED on `mangrove_fraction`, `building_density`, `road_density`,
  `ndvi_p10` — all showing the "wrong" sign. But these are all **collinear with a stronger
  same-direction driver** (mangrove↔water, building/road↔built_fraction, ndvi_p10↔ndvi_mean).
  This is SHAP credit-sharing: the model routes the signal through the strongest feature and
  the redundant partner keeps an unreliable residual sign. The data-dictionary had already
  flagged built/NDBI/impervious as near-collinear.
- **So the gate as first written was too strict** — a wrong sign on a rank-20 redundant feature
  is not a physics failure. Redesigned it to enforce physics on the **load-bearing drivers**
  (8 high-prior, non-redundant features) and merely *report* the collinear ones as
  credit-sharing. All 8 load-bearing drivers pass. This is a genuine methodological point worth
  the report: SHAP signs are only trustworthy for non-collinear features.

**Next**
- Heat Vulnerability Index (heat / population / lack-of-green, ml-methodology §5) + ward
  hotspot ranking, then the scenario engine.

---

## 2026-07-26 — Phase 2 — Modelling harness and the model ladder

**Done**
- `data_pipeline/ml/`: `dataset.py` (X, y, ward groups under ADR-0008), `cv.py` (ward-grouped
  spatial CV + naive random contrast), `train.py` (the model ladder). `scikit-learn`,
  `xgboost`, `lightgbm`, `joblib` added; `model_dir` added to config.
- Ran the ladder; **XGBoost selected, spatial R² 0.893, RMSE 1.10 °C** → `models/model.joblib`
  + `model_meta.json`. Six new tests (dataset exclusions/alignment, CV scorers); 26 total green.

**Decided**
- **Borderline features, resolved by inspection:** dropped `population` (it is *exactly*
  25 × `pop_density` — perfectly collinear), kept `land_fraction` (a real geographic property,
  not location or leakage). 30 features from the 42 columns. Logged in `dataset.py`.
- **Selection on spatial RMSE, floor excluded.** XGBoost and LightGBM tied (1.10 °C / 0.893);
  kept XGBoost. Light defaults only — no tuning warranted at ~11k × 30 (ADR-0006).

**Results — the honest number is strong, and its honesty is provable**
- Spatial R² **0.893**, RMSE **1.10 °C**: the model predicts an *unseen ward's* surface
  temperature to ~1.1 °C from physical drivers alone.
- **The random-vs-spatial gap is tiny (~0.047).** That is ADR-0008 vindicated: because absolute
  location is excluded, the model *cannot* memorise the map, so it generalises to held-out wards
  almost as well as to random cells. A large gap would have meant the score was mostly
  autocorrelation; the small gap means 0.893 is real driver-based skill. Had lat/lon been kept,
  the random R² would balloon and the gap with it.
- The mean floor is **negative** under spatial CV (−0.09) — held-out wards differ from the
  training mean, which is the ward-to-ward variation the blocked split is designed to expose.

**Next**
- SHAP on the saved XGBoost: global importance + per-cell attribution, and the **physics gate**
  — a positive `albedo` SHAP is the *expected* confound (ADR-0008), a vegetation-warms sign is a
  stop-and-fix.

---

## 2026-07-26 — Phase 2 — Kickoff: planning pass

**Done**
- ADR-0008 — spatial CV, training set, and feature policy (the three coupled decisions below).
- Expanded Phase 2 into tasks in `PROGRESS.md`; updated `ml-methodology.md` §2 to the concrete
  scheme.

**Decided (ADR-0008, author-confirmed)**
- **Ward-grouped k-fold spatial CV** — `GroupKFold` on `ward_code`, hold out whole wards.
  Chosen over a k-km block grid and k-means because wards are the unit recommendations are
  made in and the honest question is "predict an unseen ward?". The Phase 1 correlation work
  is why this is non-negotiable: `built_neigh_mean` (+0.60) ≈ `built_fraction` (+0.59), so a
  random split would place near-duplicate neighbours on both sides and inflate R².
- **Train on `land_fraction ≥ 0.5`**, predict on all land cells. Mostly-sea cells carry water
  temperature (the monotonic gradient measured in Phase 1).
- **Exclude absolute location from X** (`ward_code`, `centroid_lat/lon`) so the trees learn
  causal drivers rather than memorising the heat map — which keeps SHAP meaningful and the
  scenario engine coherent (you cannot "move" a cell). Hard-exclude `lst_p90`,
  `lst_obs_count`, `wc_pixels` as target leakage / QA.

**Learned / noted**
- The whole Phase 1 validation discipline pays its dividend here: because every feature was
  checked against physics, the Phase 2 physics gate has a precise expectation — a positive
  `albedo` SHAP is the *expected* confound, not a bug, and a vegetation-warms sign is a
  stop-and-fix. Without the Phase 1 caveats, that gate would be guesswork.

**Next**
- `ml/dataset.py` (X, y, groups with the ADR-0008 filters) and `ml/cv.py` (ward-grouped
  splitter + scorer), then the model ladder: mean floor → ridge → RF → XGBoost → LightGBM.

---

## 2026-07-26 — Phase 1 → 2 — Test suite before the modelling code

**Done**
- `tests/` with pytest — 20 tests, green in ~2 s. Split by dependency:
  - **Pure-logic (always run):** `cell_id` is the position formula and is stable when the study
    area shrinks (the guarantee that stops a boundary change repointing saved scenarios);
    `neighbourhood_mean` centre/corner/isolated; the assembly gate rejects nulls, out-of-range
    values and duplicate ids; the ward gate rejects a missing/unexpected code and the wrong CRS.
  - **Data-backed (skip if the parquets aren't built):** `features.parquet` is 11,944 × 42, has
    no all-null source column (the reducer-name-trap guard), `lst_p90 ≥ lst_mean`, WorldCover
    fractions sum to 1, unit-range columns stay in range; the real DataMeet wards pass the gate.
- `pytest>=8` in the dev group; `uv run pytest` documented in `runbook.md` §3.

**Decided**
- **Pure-logic and data-backed tests separated so a fresh clone runs green** without EE, `.env`
  or built artifacts — the data-backed ones `pytest.skip` cleanly. Locks the invariants that
  bit as silent bugs four times in Phase 1 (three reducer-name traps, `cell_id` stability)
  before modelling code — where a silent error is far more expensive to find — lands in Phase 2.
- **`test_schema_is_42_columns` is a deliberate lock:** adding or removing a feature now has to
  update the test, so schema drift is a conscious change, not an accident.

**Next**
- Phase 2 kickoff planning pass — baseline → boosted trees under spatial block CV, SHAP, HVI,
  scenario engine (where the albedo confound flag comes due).

---

## 2026-07-21 — Phase 1 — Exploration notebook: the exit-criterion render

**Done**
- `notebooks/01_explore_features.ipynb` (16 cells): reads `features.parquet` (no Earth Engine,
  runs in seconds) and renders the heat map, the LST/NDVI inverse, the driver-correlation bar
  and matrix, the ward summary table + ranking, and the hot-and-dense vulnerability scatter.
- Built with `nbformat` (valid by construction), lint-clean, and — unlike the Phase 0
  notebook — **executed headlessly end to end to verify it runs**: 0 error cells, every figure
  cell completes. Committed without outputs; the author runs it to confirm the ✅.

**Decided**
- **Colourmaps by the data's job** (dataviz method): `inferno` for LST magnitude
  (perceptually uniform, CVD-safe, brighter = hotter — not a rainbow), `YlGn` for NDVI,
  `RdBu_r` centred at zero for the correlation polarity, red/blue-by-sign for the driver bar.
  A table view accompanies the ward chart so identity is never colour-alone.
- **Land cells only for statistics** (`land_fraction ≥ 0.5`) so the sea does not skew ward
  means or correlations — the same caveat the model will apply.

**Learned**
- Executing the notebook is worth it even though the author owns the ✅: it caught nothing this
  time, but it proves the plotting code runs against the *real* table, which static checks
  cannot. The ward ranking it printed (hottest B/L/C, coolest R/C/T) matches the LST stage
  independently — a third cross-check on the whole pipeline.

**Next**
- Author runs the notebook and confirms Mumbai's heat map renders → **Phase 1 ✅**. Then the
  Phase 1 CHANGELOG entry and the Phase 2 kickoff (baseline → boosted trees, spatial block CV).

---

## 2026-07-21 — Phase 1 — features.parquet assembled

**Done**
- `data_pipeline/assemble.py` → `data/processed/features.parquet`: **11,944 rows × 42 columns,
  3.3 MB GeoParquet**. Joins all 8 sources + the LST target on `cell_id`, derives
  `impervious_fraction`, `ndvi_neigh_mean`, `built_neigh_mean`, validates, writes. Registered
  as the final `run.py` stage. Zero nulls; every column inside its physical range.

**Decided**
- **GeoParquet with geometry in the table**, not a separate join — the API and notebooks read
  one self-contained file (ADR-0004's "the file is the artifact").
- **Neighbourhood aggregates by grid-index arithmetic**, not a spatial join. `grid_row`/`col`
  make the 8 queen neighbours a lookup (ADR-0007 paying off); edge cells average what exists,
  isolated cells fall back to own value.
- **The validation gate asserts counts *and* magnitudes.** Row count, `cell_id` uniqueness,
  zero nulls in 12 required columns, and a physical-range check on 27 columns — a broken join
  or unit slip stops here, not in the model. This is the Phase 0 boundary lesson generalised:
  a bad 12k-row join has no printed area to give it away, so the check has to be deliberate.

**Learned — the correlation matrix is the whole project in one view**
- Ranked univariate correlation with `lst_mean` confirms every Phase 1 finding at once:
  warmers led by `ndbi_mean` +0.74 and the built/population cluster (~+0.55–0.60); coolers led
  by mangrove/water/NDVI (~−0.46); weather at ±0.01 (noise); and `albedo` +0.67 sitting in the
  *warmer* list — the confound, exactly where the albedo caveat said it would be.
- `built_neigh_mean` (+0.60) edges `built_fraction` (+0.59) and `ndvi_neigh_mean` (−0.43) ≈
  `ndvi_mean` (−0.45): the neighbourhood carries as much signal as the cell. That is strong
  spatial autocorrelation stated numerically — the empirical case for spatial block CV
  (ADR-0006) rather than a random split, which would leak.

**Next**
- The exploration notebook: LST + NDVI maps, correlation matrix, ward summary — renders
  Mumbai's heat map. Together with this file it is the **Phase 1 ✅ exit criterion**.
- Deferred: `lst_trend` (needs a separate per-year Landsat reduction; not required for the ✅).

---

## 2026-07-21 — Phase 1 — Open-Meteo weather (the last predictor, and it is nearly noise)

**Done**
- `sources/weather.py` → `data/interim/weather.parquet`: `air_temp_mean`, `humidity_mean`,
  `wind_speed_mean`, dry-season Mar–May 2019–2026 means from the Open-Meteo ERA5 archive.
  Registered as a `run.py` stage. **All 8 predictor sources are now built.**

**Decided**
- **Query a ~0.1° point grid (20 points), not per cell.** ERA5 is ~11 km, so 11,944 per-cell
  calls would return ~6 distinct values many times over. Cells are nearest-assigned to points.
- **Bulk requests, batched, with backoff.** The archive rate-limits by locations × days; 54
  points over 8 years hit repeated 429s. Coarsening to 20 points and sending them in one
  comma-separated request fixed it. Raw point means cached to `data/raw/`.
- **Wind in m/s** via `wind_speed_unit=ms` (the API defaults to km/h) to match the schema.

**Results — the caveat is now measured, and it points to "drop"**
- Within-city spread is tiny: air temp **1.7 °C** across the whole city, against LST's ~20 °C.
- The correlations are the real evidence: `air_temp_mean` vs `lst_mean` = **+0.02**, humidity
  −0.01, wind +0.01 — all essentially zero. Weather has **no within-city LST signal**.
- Its only spatial structure is a coarse coast proxy (humidity/wind vs `dist_coast` ≈ −0.44),
  which `dist_coast` already captures at 200 m. So the weather columns are near-redundant noise.
- Kept in the table so Phase 2 feature selection rejects them *on the record* rather than by
  omission — the honest way to retire a feature. Final call goes in `ml-methodology.md`.

**Broke / learned**
- Computing cell centroids in EPSG:4326 (degrees) warns and is subtly wrong; reproject to UTM
  first, then take the centroid. Harmless here (points are 11 km apart) but fixed properly.

**Next**
- **Assemble `features.parquet`** — join all 8 sources + neighbourhood aggregates
  (`ndvi_neigh_mean`, `built_neigh_mean`) on `cell_id`, with the row-count/null/range validation
  gate. Then the exploration notebook: the **Phase 1 exit criterion**.

---

## 2026-07-20 — Phase 1 — Landsat albedo, and a confound that could break the cool-roof tool

**Done**
- `sources/albedo.py` → `data/interim/albedo.parquet`: `albedo` (Liang 2001 broadband
  shortwave) over 11,944 cells, 0 nulls, 148 s. Registered as a `run.py` stage.
- Refactored `landsat.py`: extracted `cloud_mask()` and `dry_season_collection()` so albedo
  and LST share the exact same scenes and masking. Verified LST output byte-identical after.

**Decided**
- **Pure published Liang (2001) coefficients, no /1.016 normalisation** — matches the citation
  exactly and validated at known surfaces (sea 0.03, forest 0.12, apron 0.15, city median 0.13).
  ETM+ bands 1/3/4/5/7 → OLI SR_B2/B4/B5/B6/B7.
- **Shared the Landsat collection + cloud mask** rather than duplicate them. Byte-identical
  re-check of the LST stage confirmed the refactor changed nothing.

**Broke / learned — the important one**
- **`albedo` correlates +0.70 with LST — the wrong sign.** The feature is physically correct,
  but observationally *brighter = hotter* across the city, because dark water is cool and bright
  bare/grass/built is hot. It even holds within built cells (+0.20). **This is not a bug; it is a
  confound that inverts the cool-roof physics.** A model trained on this learns albedo→warming,
  so the digital twin would predict that whitening a roof *heats* it — the cool-roof
  recommendation, one of the project's headline interventions, would backfire.
  - **Fix, recorded for Phase 2:** the cool-roof ΔLST must come from a cited albedo-cooling
    study, not the model's coefficient, and the physics gate must expect a positive albedo SHAP.
    Flagged in `data-dictionary.md` (🚨) and `ml-methodology.md` §6.
  - This is the **fifth and most consequential** instance of the confound pattern — low-NDVI
    water, dry cropland, dist_coast/park, now albedo. The others corrupted interpretation; this
    one would corrupt an *intervention*. It is exactly what the physics gate exists to catch, and
    catching it now — before the model — is the whole point of validating every feature.
- **`reduceRegions` names a single-band mean output `mean`, not after the band.** Multi-band
  images (LST, Sentinel-2) name after the bands; a single band names after the reducer. Every
  cell came back NaN until I read `mean`. That is now three reducer-name traps (`sum`,
  `histogram`, `mean`) — a one-line `pytest` on each would have saved three debugging rounds.

**Next**
- Open-Meteo weather (last predictor, expected near-constant at 11 km), then assemble
  `features.parquet` and the exploration notebook — the Phase 1 exit criterion.

---

## 2026-07-20 — Phase 1 — OSM buildings, roads, parks — and what OSM misses

**Done**
- `sources/osm.py` → `data/interim/osm.parquet`: `building_count`, `building_density`,
  `road_density`, `dist_park` over 11,944 cells. First non-Earth-Engine source — Overpass via
  OSMnx, cell aggregation done locally, raw downloads cached in `data/raw/`. 95 s.
- 80,842 buildings, 71,361 road segments, 1,646 parks over the city.
- Added `osmnx>=2.0`.

**Decided**
- **Cache raw Overpass downloads to `data/raw/`.** Overpass is a shared free service; re-running
  the stage reads the cache, `--force-download` re-fetches. The regenerate-from-scratch
  contract still holds (ADR-0004) — the cache is a courtesy, not state.
- **Buildings assigned by representative point, roads clipped to cells.** A building counts
  once, in the cell containing its interior point; a road segment is split at cell borders and
  its clipped length summed. `drive` network only — footways would multiply the data for
  little heat signal.

**Broke / learned — three honest limitations, all documented**
- **OSM under-maps buildings, unevenly.** Median `building_density` is 0.02 and only 57% of
  cells have any building; where WorldCover says >50% built, mean OSM density is 0.16 against
  a real 0.4–0.6. Presence coverage is decent (92% of clearly-built cells have ≥1 building)
  but magnitude is undercounted, worst in informal settlements — exactly where heat
  vulnerability is highest. So `building_density` is a *relative* signal, partly redundant
  with `built_fraction` (they correlate +0.60). Google Open Buildings is parked as a more
  complete alternative for India.
- **`road_density` is the trustworthy OSM feature** — +0.69 with `built_fraction`, +0.36 with
  LST. Roads are mapped far better than individual buildings.
- **`dist_park` does not mean what the name implies.** OSM "parks" are formal urban parks and
  gardens, concentrated in the dense city; SGNP and Aarey are not tagged as parks, so
  tree-dominated cells average 412 m from the nearest "park". The result is a counterintuitive
  −0.18 correlation with LST (dense hot cores have gardens nearby; cool peripheries do not).
  Green cover is already captured properly by `ndvi_mean` and `tree_fraction`; `dist_park` is
  flagged for Phase 2 to keep or drop on evidence.
- The pattern to take forward: **validate every new source against an independent one.** OSM
  buildings vs WorldCover built, roads vs built, parks vs the tree cells — each cross-check is
  what turned "OSM is a data source" into "here is precisely what OSM gets right and wrong".

**Next**
- Landsat albedo (Liang 2001) — back in Earth Engine, the cool-roof lever the scenario engine
  needs. Then Open-Meteo weather, then assembly into `features.parquet`.

---

## 2026-07-20 — Phase 1 — SRTM terrain and distance-to-coast

**Done**
- `sources/terrain.py` → `data/interim/terrain.parquet`: `elevation_mean`, `slope_mean`,
  `dist_coast`, `dist_water` over 11,944 cells. 499 s (cumulativeCost is the heaviest source).
  Registered as a `run.py` stage.

**Decided**
- **`cumulativeCost` for distances, not `fastDistanceTransform`.** Tested FDT first; its
  pixel-unit squared-distance output inflated far distances badly — SGNP read as 34 km from a
  coast that is ~9 km away, and interior `dist_water` was ~2× too large — while near-shore
  values looked fine, so the bug would have been easy to miss. `cumulativeCost` returns metres
  directly (cost 1/pixel × pixel width), is robust to the projection scale, and validated at
  six known landmarks (Colaba, Marine Drive, SGNP, Powai, Kurla, Bandra).
- **The "sea" is large connected permanent water, not all water.** JRC GSW permanent water
  (occurrence ≥ 80%), keep only bodies > 10.24 km² (≥ 1024 px at 100 m): the Arabian Sea and
  Thane creek qualify, Powai (2 km²) and Vihar (7 km²) do not. That is what makes `dist_coast`
  (distance to tidal water) meaningfully different from `dist_water` (distance to any water) —
  Powai's are 6.7 km vs 0.2 km.
- **Distances computed on a 100 m UTM grid**, elevation/slope at native 30 m. cumulativeCost
  over a finer grid is far more expensive and a 200 m cell does not need sub-100 m distance.

**Broke / learned**
- **`ee.Projection(...)` at module import fails** — it needs Earth Engine initialised, which
  happens inside `build()`. Moved the projection construction into the image function. A
  reminder that anything touching the EE API must be lazy, not module-level.
- **The sea-breeze gradient is real but confounded by the park.** LST climbs +4 °C from the
  shore (37.7 °C) to 6 km inland (41.7 °C), then *falls* beyond 6 km (39.1 °C) — because the
  deepest interior is Sanjay Gandhi National Park, cool for vegetation/elevation reasons, not
  coastal ones. So `dist_coast` is non-monotonic with LST and its raw correlation is only
  +0.10; it is a real driver but only in combination with NDVI and elevation. Third instance
  of the same lesson (low-NDVI water cells, crop=dry-bare, now dist_coast=park): **no single
  feature separates the causes — that is what the model is for.**
- **A cheap invariant that paid off:** `dist_coast ≥ dist_water` in all 11,944 cells (the sea
  is a subset of all water). 0 violations confirms the two masks are mutually consistent.

**Next**
- OSM via OSMnx — building density/count, road density, distance-to-park. First non-Earth-
  Engine source; needs Overpass, not the reduce helper.
- Then Landsat albedo, Open-Meteo, and the assembly into `features.parquet`.

---

## 2026-07-20 — Phase 1 — WorldPop population, and the HVI signal is real

**Done**
- `sources/worldpop.py` → `data/interim/worldpop.parquet`: `population` (persons) and
  `pop_density` (persons/km²) over 11,944 cells. WorldPop `GP/100m/pop`, year 2020, 81 s.
  Registered as a `run.py` stage.

**Decided**
- **Year 2020**, the latest the collection offers (it ends at 2020) — one year inside the
  2019–2026 LST window. Closes the alignment question data-dictionary §5 had left open.
- **Sum reducer at native 100 m.** WorldPop stores a *person count* per pixel, so the cell
  value is a sum, not a mean, and a count must be summed at native resolution — reducing at a
  coarser scale would mis-count. `pop_density` divides by the full 0.04 km² cell.

**Broke / learned**
- **`Reducer.sum()` names its output `sum`, not after the band** — the same trap as
  WorldCover's `histogram`. First run read a `population` property, got 0 everywhere, and the
  total-population reconciliation guard fired: "total 0 is not near Mumbai's ~12 M". That guard
  is the whole point of the stage — a population layer that silently zeroed would be invisible
  without it. There is now a clear pattern worth internalising: **non-default reducers name
  their output after the reducer, and the shared helper must be told that name.**
- **The reconciliation is the strongest check in the pipeline so far.** Total over the grid is
  **11.7 M** against BMC's ~12.4 M census. That single number confirms units, year and mosaic
  in one shot — worth more than any range assertion.

**Results — the HVI premise holds**
- `pop_density` vs `built_fraction` **+0.74**, vs tree/water −0.31/−0.33: people live in the
  built-up cells, not the parks or the creeks, exactly as they should.
- **`pop_density` vs `lst_mean` +0.56** — population and surface heat co-locate. This is the
  finding the Heat Vulnerability Index rests on: the people are where the heat is. Without this
  correlation the HVI would be averaging two unrelated things.
- The densest cells resolve to Dharavi (G/N) and Parel (F/S) at ~65,000/km², Mumbai's known
  dense cores. 225 cells are in the top decile of *both* density and LST, clustered in Kurla,
  Ghatkopar, Parel and Dharavi — the HVI's future hotspot list, visible already in the raw data.

**Next**
- SRTM elevation + slope, then distance-to-coast/water/park. These are the terrain and
  context features; distance-to-coast is expected to matter a lot in Mumbai (sea breeze).
- Still no `pytest`; the reducer-name traps (`sum`, `histogram`) would each be a one-line
  regression test worth having before there are eight source modules to keep straight.

---

## 2026-07-20 — Phase 1 — ESA WorldCover land-cover fractions

**Done**
- `sources/worldcover.py` → `data/interim/worldcover.parquet`: nine per-class fractions per
  cell plus `wc_pixels`, over 11,944 cells, 0 empty. Single static 10 m mosaic, so the full
  grid ran in 78 s. Registered as a `run.py` stage.

**Decided**
- **Widened the class list from the planned tree/grass/built.** Inspection over four
  representative cells showed the plan missed what Mumbai actually is: the greenest cell is
  100% **mangrove** (class 95), and the hottest is 71% **cropland** (class 40). Kept all nine
  occurring classes — city composition came out built 39%, tree 34%, mangrove 10%, water 8%,
  crop 4%. Mangrove alone is 10% of the city with a −0.46 LST correlation; lumping it into
  "tree" would have hidden a major distinct cooler.
- **Frequency-histogram reducer, fractions as share of the whole cell.** The sea is class 80,
  not masked, so every cell has ~425 classified pixels and the fractions sum to 1 (asserted).
  Reduced at native 10 m — categorical class codes must be counted at native scale, never
  resampled to a coarser one.

**Broke / learned**
- **`reduceRegions` names a frequency-histogram output `histogram`, not after the band.** My
  first pass read a `Map` property and every cell came back empty; the reducer, not the band,
  names the property. Caught immediately by the "every cell empty" guard, which is exactly the
  failure that guard exists for. Fixed to read `histogram`.
- **"Cropland" in Mumbai is dry bare ground, not farmland.** Crop-dominated cells are the
  *hottest* land in the city (42.6 °C mean, above built's 41.9; 12 of the 20 hottest are
  crop). WorldCover labels the Deonar dump, fallow and dry-season bare land as cropland.
  Recorded as a caveat — using `crop_fraction` as "agriculture" would be wrong.
- **The water-disambiguation feature works, decisively.** The 285 low-NDVI *cool* cells that
  NDVI alone could not explain (the Sentinel-2 entry flagged them) have mean `water_fraction`
  0.96 vs 0.03 elsewhere. They are inland water and creeks. The reason for keeping the water
  class is now evidence, not a hunch.
- **Two independent datasets corroborate.** WorldCover fractions agree with the Sentinel-2
  indices — built↔NDBI +0.46, tree↔NDVI +0.53, water↔NDWI +0.57 — which is the cross-check
  that matters more than any single number: two different instruments telling the same story.

**Next**
- WorldPop population density per cell — the human-exposure layer, and the first that is not
  about the physical surface.
- Still no `pytest`; the WorldCover class-sum invariant and the cross-dataset checks ran as
  scratch scripts.

---

## 2026-07-20 — Phase 1 — Sentinel-2 indices, and the premise holds in the data

**Done**
- Refactored the chunked `reduceRegions` machinery out of `landsat.py` into
  `sources/_reduce.py` (shared reducer + study-region helper). Landsat now calls it —
  verified byte-identical, 0.000e+00 diff over 500 cells, so no quota re-spent.
- `sources/sentinel2.py` → `data/interim/sentinel2.parquet`: `ndvi_mean`, `ndvi_p10`,
  `ndbi_mean`, `ndwi_mean` over 11,944 cells, 542 dry-season scenes, 0 nulls. ~10.6 min.
- Registered `sentinel2` as a `run.py` stage.

**Results — the acceptance test passed**
- **NDBI vs LST = +0.74**, the strongest single relationship: built-up index drives surface
  heat harder than vegetation absence does. **NDVI vs LST = −0.45** — greener is cooler, the
  core premise, clearly present. Two sensors, independent instruments, agreeing.
- Ward cross-check is decisive: greenest wards by NDVI (R/C 0.39, T 0.33 — the national-park
  wards) are the coolest by LST; greyest (C 0.13, B, L — dense island city) are the hottest.
  This is the LST ward ranking reproduced from a completely different sensor.

**Decided**
- **30 m reduction, not 20 m.** The smoke test measured ~70 s/200 cells at 20 m (~70 min
  full grid). A 200 m cell *mean* is insensitive to sampling below ~50 m for a smooth field,
  so 30 m gives the same cell mean at ~half the cost — full grid ran in 10.6 min.
- **`S2_SR_HARMONIZED`, not `S2_SR`.** The harmonised collection removes the post-2022
  processing-baseline offset. A normalised difference is invariant to a common *scale* but
  not to an *offset*, so the offset would bias NDVI across the 2019–2026 span if unremoved.
- **SCL-band cloud masking**, water class kept — same principle as the LST QA mask. Simpler
  and more directly explainable than Cloud Score+, and dry season is low-cloud.

**Broke / learned**
- **Dropped `.filterBounds()` again** in the first draft — the collection came back as
  349,333 scenes (global) instead of 542. Same lazy-evaluation trap as the LST stage: the
  reduced values are identical either way, the only symptom is the scene count. Same guard
  now protects both stages.
- **NDVI is non-monotonic with LST at the low end.** Binning LST by NDVI, the coolest bin is
  *not* the lowest-NDVI one — cells under 0.1 NDVI include inland water, wet mangrove and
  salt pans, which are cool *and* low-NDVI. So NDVI alone cannot tell "bare hot" from "wet
  cool"; NDBI, NDWI and the WorldCover water fraction are what disambiguate. Good argument
  for the multi-feature model, and a limitation worth stating rather than hiding.
- The refactor-then-verify-byte-identical pattern is worth keeping: it let me change a
  shared code path with confidence and without re-spending Earth Engine quota to prove it.

**Next**
- ESA WorldCover land-cover fractions (tree / grass / built / water) per cell — the water
  fraction is now known to be needed to disambiguate the low-NDVI cells above.
- Still no `pytest`; the byte-identical refactor check and the index invariants ran as
  scratch scripts.

---

## 2026-07-20 — Phase 1 — The target variable: per-cell LST

**Done**
- `data_pipeline/ee_session.py` — one Earth Engine init per run, with the three known
  failure modes funnelled into a message that points at `runbook.md` §6.
- `data_pipeline/sources/landsat.py` → `data/interim/lst.parquet`. 11,944 rows,
  `lst_mean` / `lst_p90` / `lst_obs_count`. 134 scenes, 102 s for the full reduction.
- `data_pipeline/run.py` — `--stage {all,boundary,grid,landsat}`, skipping stages whose
  output exists. Completes the Phase 1 scaffolding.

**Results**
- `lst_mean` 29.8 – 50.6, mean **39.7 °C**. `lst_p90` 32.3 – 55.8, mean 43.5 °C.
- **Zero cells without a value; the sparsest has 46 cloud-free observations** (mean 58.3).
  That closes the cloud-starvation open question — no cell is starved, so `lst_obs_count`
  stays as a diagnostic rather than becoming a filter.
- **The urban heat island signal is clean: the park belt is 3.15 °C cooler than the
  southern city** (37.91 vs 41.06, inland cells only).

**Decided**
- **Chunked `reduceRegions`, 500 cells per request, 24 requests.** `reduceRegions` is
  server-side, but the result still has to come down through `getInfo`, and one call over
  12k cells exceeds the payload limit. Twenty-four requests each returning a fully reduced
  table is the "export aggregates" pattern ADR-0001 asks for — not the per-cell `getInfo`
  loop it forbids. The distinction is what is computed per request, not how many requests.
- **Cells go up as explicit polygons with `geodesic=False`.** They were built as squares in
  EPSG:32643, so their edges are straight in projection; letting Earth Engine assume
  geodesic edges would bow them slightly outward.
- **`lst_p90` is a *temporal* percentile**, not a spatial one within the cell — the hot
  years, not the hot corner. Asserted `p90 ≥ median` on every cell (0 violations), which is
  what would catch the two reducers being wired up backwards.

**Broke / learned**
- **Dropped `.filterBounds()` when promoting the notebook code.** The collection became the
  *global* archive: 349,333 scenes instead of Mumbai's 134. The values were unaffected —
  Earth Engine is lazy and spatially indexed, so it only ever computed the tiles the cells
  touched, and the smoke test returned byte-identical numbers before and after the fix.
  **That is what makes it dangerous:** the sole symptom was a scene count, and nothing would
  have failed. Now guarded by `if n_scenes > 1000: raise` — a filter that silently does
  nothing is worse than one that errors, so the check asserts the filter had an effect.
- **The cold tail is water, not vegetation, and `land_fraction` predicts it monotonically:**
  33.7 °C below 0.1 land, rising through 34.5 / 35.5 / 37.1 / 37.6 to 40.1 °C for fully
  inland cells. A 6.4 °C spread. Water is deliberately unmasked (the sea genuinely is a cool
  surface), so a mostly-sea cell reports mostly sea temperature while its predictors will
  describe the land sliver. Keeping those cells with a `land_fraction` column — rather than
  filtering at grid-build time — is what turned this from an assumption into evidence. Phase
  2 now has a real distribution to pick a threshold against.
- **Ward A looks like the coolest ward until its coastal cells are excluded**, then it falls
  to 5th. The wards that are genuinely cool are T and R/C, which hold Sanjay Gandhi National
  Park. A city-wide ward ranking published without that correction would have been wrong in
  a way that looks entirely plausible — worth remembering when the hotspot ranking is built.
- **The strongest check was again a reconciliation, not an assertion.** Phase 0's notebook
  gave a city mean of 39.8 °C over the GAUL boundary at pixel level; this pipeline gives
  39.7 °C over the ward boundary at 200 m cells with an extra year of data. Different code,
  footprint and aggregation agreeing to 0.1 °C is worth more than any range check, and the
  slight compression of the extremes (29.0→29.8, 51.6→50.6) is exactly what 200 m averaging
  should do.

**Next**
- Sentinel-2 NDVI/NDBI/NDWI. The reduction machinery in `landsat.py` generalises, so the
  chunked-`reduceRegions` helper should be lifted into a shared module rather than copied.
- Still no `pytest`. The `cell_id` stability property and the `p90 ≥ median` invariant are
  both load-bearing and both currently checked by scratch scripts.

---

## 2026-07-20 — Phase 1 — The 200 m grid and a permanent cell_id

**Done**
- `data_pipeline/grid.py` → `data/interim/grid.parquet`. **11,944 cells**, columns
  `cell_id` / `grid_row` / `grid_col` / `geometry` / `centroid_lat` / `centroid_lon` /
  `land_fraction` / `ward_code`.
- Added `pyarrow` for GeoParquet.

**Decided**
- **`cell_id = grid_row × 1_000_000 + grid_col`, anchored to the EPSG:32643 origin.** The
  obvious alternative — a sequential `0..N` over whatever cells come out — is a trap. Drop
  one coastal cell and every id after it shifts by one, so a stored scenario keeps its
  number and silently points at different ground. Anchoring to the projected CRS makes an
  id a property of *where the cell is on Earth*, so re-running against a revised boundary
  adds and removes cells but renumbers nothing.
  **Verified rather than asserted:** rebuilding without ward T gives 10,891 cells, all of
  which carry their original ids, and zero ids appear that were not in the full grid.
- **Grid built in EPSG:32643, stored in EPSG:4326.** A 200 m cell defined in degrees is
  neither square nor constant in size with latitude. Centroids are likewise computed in UTM
  and converted afterwards. This is the split `conventions.md` already mandated; the grid is
  the first place it actually bites.
- **`grid_row`/`grid_col` are kept as columns, not just folded into the id.** Neighbourhood
  features (`ndvi_neigh_mean`, `built_neigh_mean`) become integer arithmetic on the row/col
  lattice instead of a spatial join over 12k polygons.
- **Coastal slivers are kept, with `land_fraction` recording how much land each holds.**
  Filtering here would bake a guess into a permanent cell set. Phase 2 can drop or
  down-weight low-`land_fraction` cells on evidence, which is reversible; deleting them now
  is not.
- **Ward by majority overlap**, from the same overlay that produces `land_fraction`, so the
  two can never disagree about which geometry they came from.

**Learned / noted**
- The strongest correctness check turned out to be a reconciliation, not an assertion: total
  cell land area **458.3 km²** against ward area **458.3 km²**, difference −0.00. If the
  overlay had double-counted, dropped a ward, or mismatched a projection, that number would
  not close. It is worth more than any single unit test here.
- Per-ward counts sanity-check against area independently: R/C is 48.03 km² and gets 1,259
  cells; C is 1.91 km² and gets 52. At 0.04 km² per cell those are the right magnitudes,
  with the excess explained by partial edge cells.
- 92.1% of cells are fully inland, 1.6% hold under a tenth of a cell of land. The
  distribution is printed on every run so a future boundary change shows up immediately as
  a shifted profile.

**Next**
- Promote the Phase 0 Landsat code into `sources/landsat.py` and reduce LST to per-cell
  `lst_mean` / `lst_p90` / `lst_obs_count`. That is the first stage that spends Earth Engine
  quota against the real grid, so `--stage` caching in `run.py` matters from here on.

---

## 2026-07-20 — Phase 1 — Ward boundaries, and the study area is 458 km² not 603

**Done**
- `data_pipeline/config.py` — `pydantic-settings`, replacing the notebook's bare `dotenv`.
  Resolves `DATA_DIR` against a repo root derived from `__file__`, so stages behave
  identically whichever directory they are launched from.
- `data_pipeline/boundary.py` — caches the DataMeet source under `data/raw/`, validates it,
  writes `data/processed/wards.geojson`. Runs as `uv run python -m data_pipeline.boundary`.
- Output: 24 wards, EPSG:4326, columns `ward_code` / `area_km2` / `geometry`, 573 KB.

**Decided**
- **The gate is the exact set of 24 ward codes, not the count.** Phase 0's bug passed a
  `count != 0` check while matching one district of two. A count check answers "did I get
  something?"; a set check answers "did I get the *right* thing?". No truncated or wrong
  dataset reproduces all 24 of A…T with the E/W and N/S splits. Verified by deleting a ward
  and confirming the failure names it: `missing=['T']`.
- **Area is reported, not tightly gated.** No two sources agree on Mumbai's area, so a
  narrow band around any one figure would reject a legitimate source. The band is
  380–700 km²: wide enough for any real Mumbai boundary, narrow enough to reject a
  different city entirely.
- **Wards must tile** — `sum(areas) == area(union)` within 0.5 km². Overlapping wards would
  let one cell belong to two wards and silently double-count every ward-level aggregate.
- **6 decimal places on write.** float64's ~15 digits produced 972 KB; RFC 7946's
  recommended 6 dp (~0.11 m) gives 573 KB, for an area difference of 167 m² across the
  entire city — 0.000036%. No vertices removed, 29 coincident points collapsed. Storing
  precision the source survey never had is not worth 400 KB in git.
- **`ward_code` only; `ward_name` deferred.** The source's `name` field holds the BMC code
  ("A", "R/C"), not a place name. Mapping R/C→Borivali from memory would be precisely the
  invented-label problem `conventions.md` forbids. It needs a citable source first.

**Broke / learned**
- **The study area is 458 km², not the 603 km² that five documents asserted.** 603 is the
  two *districts* (Mumbai City 157 + Mumbai Suburban 446), which include harbour, creek and
  tidal area that no ward polygon covers. FAO GAUL independently measures 487. All three
  describe different footprints; this project's is the ward union, 458 km².
- **Consequence: ~11–12k cells at 200 m, not the "15–20k" written into BLUEPRINT.**
  ADR-0007's *decision* is unaffected — 11.5k is still comfortable for boosted trees, and
  it strengthens rather than weakens the rejection of 300 m (~5k rows). But the supporting
  figure inside that ADR is now known to be wrong, and `conventions.md` makes ADRs
  immutable, so it stays as written. The corrected number lives in `data-dictionary.md`,
  which is the living spec. **Open question for the author:** whether "immutable" permits
  an appended dated correction note, or whether a stale supporting figure is simply what an
  ADR is — a record of what was known at decision time.
- **Checked SGNP coverage explicitly before trusting the dataset**, because a heat study
  that excluded the city's largest cool surface would be broken in a way no schema check
  catches. Kanheri Caves resolves to ward R/C; Aarey, Powai and Vihar are all inside. The
  park is in.
- The wards tile exactly — sum equals union, no interior holes — so the missing 145 km² is
  a notch in the outer boundary (coastline, creeks) rather than a hole punched in the
  middle. That is what ruled out the "SGNP is excluded" hypothesis before writing any code.

**Next**
- The 200 m grid and `cell_id`. Everything above exists so that stage has a validated
  polygon to clip to.

---

## 2026-07-20 — Phase 1 — Kickoff: planning pass

**Done**
- Phase 0 closed: exit criterion ticked, CHANGELOG entry written, `architecture.md` checked.
- ADR-0007 — 200 m analysis grid.
- `data-pipeline/` → `data_pipeline/`, now an installable package (hatchling) so
  `python -m data_pipeline.run` works as `runbook.md` §3 already documented.
- Phase 1 expanded into grouped tasks in `PROGRESS.md`: scaffolding → geometry → target →
  predictors → assemble.

**Decided**
- **Ward boundaries: DataMeet `Municipal_Spatial_Data`, `Mumbai/BMC_Wards.geojson`,
  CC BY 4.0**, already EPSG:4326. This closes the longest-standing open question in
  `data-dictionary.md` §5. A materially better licence than GAUL's restricted
  redistribution, and it comes with a trap: the same folder ships
  `bmc_electoral_wards_2017`, the 227 *electoral* wards. This project uses the **24
  administrative** wards — those are the units MCAP is written against and that budgets
  follow. Ranking electoral wards would produce a result no planner could act on.
- **200 m grid (ADR-0007).** The deciding argument is the *direction* of the resolution
  claim: Landsat thermal is 100 m native (the 30 m delivery grid is packaging, not
  information), so a 200 m cell averages ~4 measured pixels and sits deliberately coarser
  than the instrument. Nothing is ever downscaled. 100 m was rejected because one pixel per
  cell means no averaging and co-registration error propagates undiluted; 300 m because it
  blurs the ~200 m scale at which a park or a block of cool roofs actually exists.
- **Years: Mar–May 2019–2026.** Phase 0 measured 56 scenes over 2019–2025 after cloud
  filtering, so the range is known-good; 2026 is complete and free, giving an 8th year for
  `lst_trend`. Decided from evidence rather than guessed, which is the point of having run
  Phase 0 first.
- **Renamed the pipeline directory now.** `data-pipeline` with a hyphen is not a legal
  Python module name, so the `python -m data_pipeline.run` in the runbook could never have
  worked. The folder held one `.gitkeep`, so the fix cost nothing today; after three weeks
  of imports it would have been a refactor.

**Learned / noted**
- `architecture.md` §3 claimed pipeline output is "committed as data artifacts". It is the
  opposite — `data/processed/` and `models/` are gitignored build outputs, and ADR-0004's
  whole argument is that excluding them is safe *because* they are regenerable. Left
  standing, that sentence would have quietly licensed committing a 50 MB parquet in Phase 1.
  Caught only because `conventions.md` requires an architecture check at phase close, which
  is the first time that rule has earned its keep.

**Next**
- First code task: fetch and validate BMC wards → `data/processed/wards.geojson`, gated on
  24 wards and total area ≈ 603 km².
- Then the 200 m grid and `cell_id`. That builder deserves the most scrutiny of anything in
  Phase 1: `cell_id` is permanent once assigned, and every saved scenario, stored model and
  cached API response downstream is keyed on it.

---

## 2026-07-19 — Phase 0 — Python environment and the Earth Engine hello-world notebook

**Done**
- Python environment: `pyproject.toml` + `uv.lock`, pinned to 3.12 via `.python-version`.
  `uv sync` installs 151 packages — `earthengine-api` 1.7.35, `geemap` 0.38.3,
  `geopandas` 1.1.4, JupyterLab, `ruff`.
- `notebooks/00_hello_earth_engine.ipynb`, 25 cells: authenticate → GAUL Mumbai boundary →
  Landsat 8/9 C2 L2 dry-season composite → numeric sanity check → interactive map → static
  PNG → NDVI cross-check.
- `runbook.md` §1.5, §2 and §6 corrected to match the setup that actually exists.
- Earth Engine registered against the `urbanheat-mumbai` Cloud project (noncommercial,
  academic) and the notebook run end to end: 56 Landsat scenes, both Mumbai districts,
  LST composite rendered as both an interactive map and a static PNG.

**Decided**
- **Python 3.12, not the system 3.14.** `geopandas`/`pyproj`/`shapely` wheels lag the newest
  CPython, and a source build needs a GEOS/PROJ toolchain that is miserable on Windows. 3.12
  satisfies "3.11+" with full wheel coverage, and `.python-version` makes the venv
  reproducible rather than dependent on whatever `python` resolves to.
- **`pyproject.toml` + `uv.lock` instead of `requirements.txt`.** The runbook originally
  specified `requirements.txt`; a lockfile pins the full transitive graph, which is what
  ADR-0004's "must be regenerable by re-running the pipeline" contract actually needs.
- **`python-dotenv` in the notebook, not `pydantic-settings`.** `conventions.md` mandates
  pydantic-settings for *modules*, and explicitly scopes notebooks as exploration. The
  settings module lands in Phase 1, when `data-pipeline/` exists and there is more than one
  consumer to share it with. Deferred deliberately, not overlooked.
- **FAO GAUL 2015 level-2 as the Phase 0 boundary.** Already in the EE catalog, so no
  download and no shapefile handling. Greater Mumbai spans two GAUL districts (Mumbai +
  Mumbai Suburban), dissolved into one polygon. A placeholder by design — and its licence
  turns out to restrict redistribution, which is a second, independent reason Phase 1's
  swap to BMC/OSM wards is the right call (`data-dictionary.md` §1, §5).
- **Verify LST numerically before plotting.** The notebook prints min/mean/max °C before any
  map cell. A map renders a picture whether or not the scale factor was applied; only the
  numbers catch it.

**Learned / noted**
- The two Collection 2 scale factors are easy to confuse and fail differently. Thermal is
  `× 0.00341802 + 149.0` (→ Kelvin); optical is `× 0.0000275 − 0.2` (→ reflectance 0–1).
  Applying the optical factor to `ST_B10` yields ~0.15 — wrong enough to ruin the model,
  plausible enough to go unnoticed. Failure table in notebook §3.1.
- `QA_PIXEL` masking rejects four bits, not one: cloud (3), shadow (4), cirrus (2), dilated
  cloud (1). Cirrus is the dangerous one — invisible in a true-colour preview while still
  attenuating the thermal signal. Water (bit 7) is deliberately kept; the sea and the lakes
  are genuine cool surfaces, not errors.
- Band arithmetic drops image metadata in Earth Engine. `system:time_start` has to be
  carried forward with `copyProperties` or the per-year work in Phase 1 breaks silently.
- **Boundary bug — a partial match that raised no error.** GAUL spells the island city
  `Mumbai city` (lowercase "c"); the hardcoded list said `Mumbai`, so `ee.Filter.inList`
  matched only `Mumbai Suburban` and the study area silently lost ~78 km² of the densest
  part of the city. Caught by the printed area (409 km², against ~603 expected), not by
  any exception. **The guard was the real defect:** it tested `n_matched == 0`, which only
  catches total failure. A partial match is the dangerous case — it yields a valid geometry
  that is quietly incomplete, and every downstream statistic inherits the omission. Now
  asserts `n_matched == len(MUMBAI_DISTRICTS)` and prints the matched names on failure.
  General lesson for Phase 1: **validate the count and the magnitude, never just
  non-emptiness.**
- **GAUL under-measures Mumbai by ~19%** — 487 km² against BMC's published 603 km². Not a
  bug; GAUL is a generalised global product that smooths coastlines, and Mumbai is built
  substantially on reclaimed land. Harmless for a Phase 0 picture, but it is a third
  independent reason (alongside no ward geometry and the redistribution licence) that
  Phase 1 must use real BMC polygons. The notebook now prints the gap as a percentage
  rather than a pass/fail verdict.
- **Authentication took three separate failures to clear**, none of them code:
  1. The paste-code flow produced a code that was never redeemed — it has to go into the
     prompt of the *same* run, since the PKCE verifier is per-session.
  2. `earthengine authenticate` with the default auth mode returned "This app is blocked"
     — the college Workspace domain blocks that OAuth client. Different `--auth_mode`
     values use *different* clients, so notebook mode worked where the default did not.
  3. `ee.Initialize` then returned 403 `SERVICE_DISABLED`: the Cloud project existed but
     had never been registered with Earth Engine. Creating a project and registering it
     are separate steps. Registration enables `earthengine.googleapis.com` as a side
     effect. All three are now rows in `runbook.md` §6.
- **First real numbers**, Mar–May 2019–2025, 56 scenes after cloud filtering, clipped to
  the GAUL land boundary: min 29.0 °C, mean 39.8 °C, max 51.6 °C.
- **The predicted 30–36 °C mean was miscalibrated, and the code was right.** The prediction
  assumed sea-surface pixels were in the region; an administrative *land* boundary excludes
  them, so the minimum is the coolest land (park canopy) rather than water, and everything
  shifts up. Worth remembering that a "plausible range" is a property of the clip footprint
  as much as of the retrieval — comparing against a published figure that used a different
  footprint would be an error. §4's table now carries observed values, not guesses.

**Next**
- Visual confirmation of the LST/NDVI inverse relationship — Sanjay Gandhi National Park
  and Aarey cool, Dharavi and the eastern industrial belt hot. The one check that cannot
  be automated, and the last thing standing between here and the Phase 0 ✅.
- Phase 1 kickoff: BMC ward boundaries → `data/processed/wards.geojson`, then the ~200 m
  grid with stable `cell_id`.
- **Carry into Phase 1:** assert counts *and* magnitudes on every join and filter, never
  just non-emptiness. The boundary bug above is the cheap version of a defect that would
  be far more expensive to find inside a 20k-row feature table, where no printed area
  number would be sitting there to contradict it.

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
