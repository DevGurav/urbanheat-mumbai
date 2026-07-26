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
