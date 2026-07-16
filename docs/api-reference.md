# API Reference

Endpoint contracts and the reasoning behind them. FastAPI generates the authoritative
OpenAPI schema at `/docs`; this file carries the *why* that the schema cannot.

**Status:** planned contract (Phase 3). Kept in sync as endpoints land — an endpoint added
or changed requires an update here ([conventions.md](conventions.md)).

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

## `GET /city/grid`
The choropleth layer — the dashboard's main payload.

| Param | Type | Default | Notes |
|---|---|---|---|
| `layer` | `lst` \| `ndvi` \| `hvi` \| `built` | `lst` | Which value to return |
| `simplify` | float | `0.0001` | Geometry tolerance (°) |
| `bbox` | `minx,miny,maxx,maxy` | — | Optional viewport filter |

Returns GeoJSON FeatureCollection: `cell_id`, `value`, `ward_name`.

> **Bandwidth.** ~20k polygons is multi-MB raw — real money against Render's 5 GB/mo free
> allowance (ADR-0003). Hence geometry simplification, gzip, and a long cache TTL: the grid
> only changes when the pipeline re-runs. If this still proves heavy, the fallback is
> pre-rendered vector tiles rather than a bigger plan.

## `GET /hotspots`
`n` (default 10) · `by` = `hvi` | `lst` · `unit` = `ward` | `cell`
Ranked list with value, population, and the top SHAP driver per entry.

## `GET /explain/{cell_id}`
Per-cell SHAP attribution — **the product's core answer to "why".**
```json
{
  "cell_id": 8421, "ward_name": "Kurla",
  "lst_mean": 41.3, "city_mean": 36.8, "deviation": 4.5,
  "measurement": "land_surface_temperature",
  "drivers": [
    {"feature": "ndvi_mean", "value": 0.08, "shap_c": 2.1, "direction": "warming"},
    {"feature": "built_fraction", "value": 0.87, "shap_c": 1.4, "direction": "warming"},
    {"feature": "dist_coast", "value": 6200, "shap_c": 0.9, "direction": "warming"}
  ],
  "model_version": "lgbm-v1"
}
```
*(Illustrative shape — values are placeholders until Phase 2.)*

## `POST /scenario`
The digital twin.
```json
{"target": {"ward": "Kurla"}, "intervention": "tree_planting", "coverage": 0.2}
```
Returns per-cell ΔLST, summary stats, cost range, **and**:
```json
{"clamped": true, "clamped_cells": 12,
 "caveat": "Correlational model. Cells with similar characteristics but higher NDVI show
            ~1.8 °C lower surface temperature; this is not a causal prediction."}
```
> `clamped` is not decoration. Scenarios pushing features past the training envelope get
> clamped (ADR-0006) and the response **must** disclose it — a silently capped number that
> looks like a real one is the failure mode this field exists to prevent.

## `GET /trends`
`ward` optional. Per-year Mar–May median LST + fitted slope (°C/yr). Needs ≥5 years.

## `GET /weather`
Open-Meteo passthrough, cached. `days` (default 7).

## `POST /agent/chat`
```json
{"message": "Which 5 wards need trees most urgently?", "session_id": "uuid"}
```
Returns narrative text, `tool_calls` made (transparency — the panel will ask), optional
GeoJSON layer, `agent` that handled it.
> Slow (multi-second, LLM-bound) and rate-limited (~10/min — ADR-0002). The client shows a
> thinking state and surfaces 429s honestly rather than retrying silently.

## `GET /alerts`
Polled, not pushed (ADR-0003). Daily-refreshed feed: severity, wards, summary, timestamp.
Advisory only — not an official IMD warning.

## `POST /reports/generate` *(Phase 7)*
WeasyPrint PDF for a ward or scenario. Returns a download URL.

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
