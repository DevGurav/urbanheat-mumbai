# API Reference

Endpoint contracts and the reasoning behind them. FastAPI generates the authoritative
OpenAPI schema at `/docs`; this file carries the *why* that the schema cannot.

**Status:** Phase 3 complete — all data/model/scenario endpoints below are ✅ *(landed)* and
demoable from `/docs` locally. `/agent/chat`, `/alerts` and `/reports/generate` are Phase 4/7
contracts, not yet built. Kept in sync as endpoints land — an endpoint added or changed
requires an update here ([conventions.md](conventions.md)).

**Base** `http://localhost:8000` (dev) · Render URL (prod)
**Format** JSON; geometry as GeoJSON, EPSG:4326
**Auth** none through Phase 5; Supabase JWT on write endpoints from Phase 6

---

## Conventions

- Temperatures are **surface** temperature in °C. Field names say `lst_*` and responses
  carry a `measurement: "land_surface_temperature"` marker so a client cannot mistake them
  for air temperature (ADR-0005).
- Every response carrying model output includes `model_version` and `data_version`.
- Errors: RFC-7807-ish `{detail, error_code}` with a real HTTP status. Never a 200 with an
  error message inside.
- Money is a `{min, max, currency, basis}` range, never a point estimate
  (`ml-methodology.md` §6).

---

## `GET /health`
Liveness + versions. Also the endpoint used to wake Render before a demo.
```json
{"status": "ok", "model_version": "...", "data_version": "...", "uptime_s": 12}
```

## `GET /city/grid` ✅ *(landed)*
The choropleth layer — the dashboard's main payload.

| Param | Type | Default | Notes |
|---|---|---|---|
| `layer` | `lst` \| `ndvi` \| `hvi` \| `built` | `lst` | Which value to return |
| `simplify` | float | `0.0001` | Geometry tolerance (°); `0` disables simplification |
| `bbox` | `minx,miny,maxx,maxy` | — | Optional viewport filter; 400 if malformed |

Returns GeoJSON FeatureCollection: `cell_id`, `value`, `ward_code`. The `hvi` layer only
covers land cells (`hvi.parquet` is built over `land_fraction >= 0.5`, ADR-0008) — it is a
strict subset of the other three layers, not an error.

> **Bandwidth.** ~12k polygons is multi-MB raw — real money against Render's 5 GB/mo free
> allowance (ADR-0003). Measured: default simplify + gzip brings the full-city `lst` layer
> from ~4 MB to **~460 KB**. Geometry simplification, gzip, and a long client-side cache TTL
> (the grid only changes when the pipeline re-runs) are enough; vector tiles are not needed.

## `GET /hotspots` ✅ *(landed)*
`n` (default 10, max 100) · `by` = `hvi` | `lst` · `unit` = `ward` | `cell`
Ranked list with value, population, and the top SHAP driver per entry (mean |SHAP| per
feature for `unit=ward`; that cell's own SHAP row for `unit=cell`). `top_driver_shap_c` (the
signed °C contribution) is only meaningful at `unit=cell` — a ward's driver is a mean-|SHAP|
ranking, not one signed number, so it's `null` there.

## `GET /explain/{cell_id}` ✅ *(landed)*
Per-cell SHAP attribution — **the product's core answer to "why".**
```json
{
  "cell_id": 10453001345, "ward_code": "A",
  "lst_mean": 36.65, "city_mean": 39.96, "deviation": -3.31,
  "measurement": "land_surface_temperature",
  "drivers": [
    {"feature": "water_fraction", "value": 0.263, "shap_c": -1.049, "direction": "cooling"},
    {"feature": "ndbi_mean", "value": -0.019, "shap_c": -0.774, "direction": "cooling"},
    {"feature": "dist_water", "value": 127.8, "shap_c": -0.712, "direction": "cooling"}
  ],
  "model_version": "xgboost-v1"
}
```
*(Real response, captured from a local run — no longer a placeholder.)* `top` query param
(default 3, max 10) controls how many drivers come back. 404 with `cell_not_found` for an
unknown `cell_id`; 404 with `cell_not_explained` for a real cell below the training
land-fraction threshold (mostly sea — SHAP was never computed for it, `ml/explain.py`).

> **Deviation from the original contract:** every field named `ward_name` above is
> `ward_code` in the real response. `data-dictionary.md` §grid records that `ward_name` was
> never populated — the BMC source supplies only the ward code, and an official name mapping
> needs a citable source before it's added (not invented here).

## `GET /predict` ✅ *(landed)*
The model's own LST prediction for one cell, alongside the observed value — a transparency
endpoint, not a what-if tool (that's `/scenario`). `cell_id` required.
```json
{"cell_id": 10453001345, "ward_code": "A", "predicted_lst": 36.52, "observed_lst": 36.65,
 "residual": 0.13, "measurement": "land_surface_temperature", "model_version": "xgboost-v1"}
```
404 `cell_not_found` / `cell_not_predictable` (below the training land-fraction threshold —
same restriction as `/explain`, the model was never trained on mostly-sea cells).

## `POST /scenario` ✅ *(landed)*
The digital twin.
```json
{"ward_code": "L", "intervention": "greening", "coverage": 1.0}
```
`intervention` is `greening` | `cool_roof` (not the draft's `tree_planting` — matches
`ml/scenario.py`'s two actual levers). `coverage` only applies to `cool_roof`; greening always
raises NDVI to a fixed target rather than a coverage fraction, and `coverage` is ignored for it
— a real limitation of the current model, not hidden.

Returns per-cell ΔLST + summary stats, **and**:
```json
{"clamped": false, "clamped_cells": 0,
 "caveat": "Correlational model, SHAP-validated NDVI cooling (Grover & Singh 2015 report
            ~1.39 °C per unit NDVI in Indian metros). 'Cells like this but greener are
            cooler' — not a causal guarantee for this specific cell."}
```
> `clamped` is not decoration. Scenarios pushing features past the training envelope get
> clamped (ADR-0006) and the response **must** disclose it — a silently capped number that
> looks like a real one is the failure mode this field exists to prevent. Cool-roof never
> clamps by construction (it's a cited formula, not a model call).

**No `cost` field.** The original contract sketched a `{min, max, currency, basis}` cost
range. `references.md` has no cited cost-per-area figure for either lever — "a cost or ΔLST
figure without a source is a fabrication" applies to cost exactly as it does to the cooling
coefficients. Add the field once a source is logged there, not before.

## `GET /trends`
`ward` optional. Per-year Mar–May median LST + fitted slope (°C/yr). Needs ≥5 years.
**Stubbed ✅** (author-confirmed at Phase 3 kickoff): `lst_trend` was never built (deferred in
Phase 1), so this returns `{"available": false, "note": "..."}` rather than fake a slope.

## `GET /weather` ✅ *(landed)*
Open-Meteo *forecast* passthrough for one city-representative point, TTL-cached (30 min,
in-process). `days` (default 7, max 16). Distinct from the pipeline's `sources/weather.py`
stage, which builds historical per-cell dry-season means as a model feature — that stage's own
finding (ERA5-scale weather barely varies across 458 km²) is why one point is enough here.

## `POST /agent/chat` ✅ *(landed)*
```json
{"message": "Which 5 wards need trees most urgently?", "session_id": null}
```
`session_id` is accepted for contract compatibility but not yet used — no persisted
conversation memory (`agents.md` didn't specify a multi-turn design; each call is a fresh,
stateless dispatch). One classification call routes to Copilot, Planning or Digital Twin
(`agents.md` §2); Monitoring is never reachable here — it is cron-triggered, not chat-triggered
(`agents.md` §7).
```json
{
  "agent": "digital_twin",
  "text": "Cells like this one, but greener, run about 0.65 °C cooler on average...",
  "tool_calls": [
    {"name": "simulate_scenario", "args": {"ward_code": "A", "intervention": "greening"},
     "result": "{\"ward_code\": \"A\", \"mean_dlst\": -0.65, ...}"}
  ],
  "layer": {"type": "FeatureCollection", "features": ["..."]}
}
```
`layer` is a GeoJSON FeatureCollection built from a `simulate_scenario` call, or `null` if the
agent didn't make one — not every answer has a map. `503 agent_layer_unavailable` if the RAG
index or `GEMINI_API_KEY` isn't configured at all; `503 agent_upstream_unavailable` if a
present key fails at call time (a broken key can't be caught at startup without spending a
real call to check — `runbook.md`'s `403 PERMISSION_DENIED` entry is exactly this case, open
as of 2026-07-27).
> Slow (multi-second, LLM-bound) and rate-limited (~10/min — ADR-0002). The client shows a
> thinking state and surfaces 429s honestly rather than retrying silently. **Response caching
> and 429 backoff/Groq-fallback are not built yet** — Rate-limit hygiene, the next task group.

## `POST /monitoring/check` ✅ *(landed)*
The HTTP trigger point for the daily GitHub Actions cron (`architecture.md` §6: GA → trigger
→ Render; `agents.md` §7) — not reachable from `/agent/chat`, Monitoring is never chat-routed.
Runs the deterministic threshold check (`backend/agents/monitoring.py`, ADR-0010) and, only if
triggered, logs it with dedupe (`backend/agents/alerts.py` — one entry per event or escalation,
not per run) and drafts the wording.
```json
{"triggered": true, "alert": {"date": "2026-07-27", "severity": "heat_wave",
 "forecast_max_c": 46.0, "wards_affected": ["B", "L", "C", "H/E", "F/S"],
 "summary": "...", "caveat": "Based on forecast air temperature against IMD's absolute..."}}
```
`{"triggered": false, "alert": null}` most days — Mumbai rarely reaches the 45 °C threshold
(ADR-0010's own stated consequence). The GitHub Actions workflow itself
(`.github/workflows/monitoring.yml`) is a no-op until Phase 6 sets a `BACKEND_URL` secret —
there is no deployed backend yet for it to call.

## `GET /alerts` ✅ *(landed)*
Polled, not pushed (ADR-0003). `limit` (default 50, max 200). Newest first; each entry is the
same shape `POST /monitoring/check` returns, read back from `backend/agents/alerts.py`'s
append-only log. Advisory only — not an official IMD warning (every entry's own `caveat`
field says so).

## `GET /auth/me` ✅ *(landed)*
The first write-adjacent endpoint with real auth (Phase 6). Requires `Authorization: Bearer
<token>` — a Supabase session access token, obtained client-side after the magic-link
sign-in completes. Verified by asking Supabase's own `/auth/v1/user` rather than decoding the
JWT locally (`backend/auth.py`'s module docstring has the tradeoff); every other endpoint
above stays open and unauthenticated.
```json
{"id": "3fae2b1a-...", "email": "planner@example.com"}
```
`401 unauthenticated` (no/malformed bearer token) · `401 invalid_token` (expired or bad
session) · `503 auth_not_configured` (no Supabase project wired up — the honest failure mode
on a fresh clone before `runbook.md` §1.4 is done) · `503 auth_upstream_unavailable` (Supabase
itself unreachable).

## `GET /scenarios` · `POST /scenarios` · `DELETE /scenarios/{id}` ✅ *(landed)*
Saved scenario **configs**, not computed results (Phase 6) — all three require the same
`Authorization: Bearer <token>` as `GET /auth/me`, and all three restrict a caller to their
own rows via Postgres RLS (`supabase/schema.sql`), not a backend-side `user_id` filter: every
call forwards the caller's own token to PostgREST rather than using the service-role key.
```json
{"ward_code": "L", "intervention": "greening", "coverage": 1.0}
```
`POST` mirrors `ScenarioRequest`'s exact fields and constraints, so a saved row can never
describe a scenario `/scenario` would reject. Returns the created row (`id`, `saved_at` added
server-side). `GET` returns `{"scenarios": [...]}`, newest first. `DELETE` returns `204` on
success; `404 scenario_not_found` for an id that doesn't exist **or belongs to someone
else** — RLS makes those look identical on purpose, so the response can't leak which is true.

**Why config, not a result:** loading a saved scenario means the frontend calls the real
`POST /scenario` with these fields — the number a user sees is always freshly computed
against the current model, never a snapshot that silently drifted from a retrained one.

## `POST /reports/generate` ✅ *(landed)*
```json
{"ward_code": "L", "intervention": "greening", "coverage": 1.0}
```
`intervention` optional — omit it for a ward-explanation-only report, no scenario section.
Both sections reuse `explain_ward`/`scenario` (`backend/services.py`) — the PDF never
computes a number itself, only formats one the API already serves.

Returns the PDF **directly** (`application/pdf`, `Content-Disposition: attachment`), not a
stored-file URL as originally sketched — the same kind of correction Phase 3 already made to
this file's draft contracts (`ward_name` → `ward_code`, `tree_planting` →
`greening`/`cool_roof`). Storing the file somewhere would mean adding blob storage this
project has never needed anywhere else (ADR-0004); streaming the bytes back on the same
request needs nothing new.

`404 ward_not_found` / `ward_has_no_land_cells` (same as `POST /scenario` — reuses its
validation). `503 reports_unavailable` if WeasyPrint's native Pango/cairo libraries aren't
importable on the host — present in the deployed image and CI (`Dockerfile`, `ci.yml`), not
guaranteed on every dev machine (`backend/reports/generate.py`'s module docstring).

---

## Planned status codes

| Code | When |
|---|---|
| 400 | Invalid params (bad bbox, coverage > 1) |
| 404 | Unknown `cell_id` / ward |
| 422 | Pydantic validation failure |
| 429 | LLM rate limit hit — surfaced, with `retry_after` |
| 503 | Model or feature table not loaded |

## Open questions for Phase 3

- [ ] Is `/city/grid` fast and small enough as GeoJSON, or are vector tiles needed?
- [ ] Should `/agent/chat` stream? SSE would improve the demo, but adds a moving part —
      decide once real latency is known
- [ ] Cache TTLs per endpoint
- [ ] Rate limiting on `/agent/chat` (slowapi) to protect the upstream free tier
