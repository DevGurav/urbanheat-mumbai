# ADR-0004 — Files first, Supabase later

**Status:** Accepted
**Date:** 2026-07-17
**Phase:** 0

## Context

The diagram calls for PostgreSQL + PostGIS holding users, cities, boundaries,
infrastructure, reports, metadata and logs. But the data splits cleanly into two kinds:

- **Analytical, read-only, regenerable** — the ~20k-cell feature table, ward polygons,
  model artifacts. Written once per pipeline run, read on every request, never mutated by
  a user, and reproducible from `data-pipeline/` at any time.
- **Transactional, user-generated** — accounts, saved scenarios, alert history. Small,
  mutable, and needs to survive a redeploy.

Only the second kind actually needs a database. The first is a file that happens to be
tabular. Setting up Postgres in Phase 1 would mean an ORM, migrations, a spatial extension
and a connection pool standing between a notebook and its own data — during the phase whose
entire purpose is fast iteration on feature engineering.

## Options considered

### A — Supabase (Postgres + PostGIS) from Phase 1

**Pros** Matches the diagram immediately; one storage story throughout; PostGIS spatial
queries available from the start; no migration work later.
**Cons** Every pipeline iteration becomes a schema migration; a notebook exploring features
has to round-trip through a network database instead of reading a local file; free tier
pauses after ~1 week of inactivity — exactly what happens over a semester break — and an
unpaused-database error during Phase 2 would block ML work; PostGIS is unnecessary when
every geometry operation happens upstream in Earth Engine or in-process in GeoPandas.

### B — GeoParquet + GeoJSON files through Phase 5, Supabase from Phase 6

**Pros** A notebook reads `features.parquet` in one line, no schema and no server; columnar
compression makes ~20k rows a couple of MB; the file is the artifact — versioned, diffable
in size, trivially shared; GeoPandas + Shapely cover every spatial operation needed at this
scale; the database arrives exactly when the first genuinely transactional feature (auth,
saved scenarios) does.
**Cons** No SQL over features; no concurrent writers (irrelevant — one pipeline, one
author); a migration is deferred rather than avoided; spatial *queries* must be done in
Python instead of PostGIS.

### C — SQLite + SpatiaLite throughout

**Pros** SQL without a server; a single file.
**Cons** SpatiaLite is awkward to install on Windows; no meaningful gain over parquet for a
read-only analytical table; still no answer for hosted auth in Phase 6.

## Decision

**Option B — files through Phase 5, Supabase (free) from Phase 6** for users, saved
scenarios and alert history. The feature table stays a file permanently.

The deciding factor is that the analytical data is *regenerable and read-only* — the
defining properties of a build artifact, not database state. Introducing a database for it
adds ceremony to the phases that most need velocity, and the free tier's idle-pause turns
that ceremony into an outage risk during the exact weeks the ML work happens. When a
genuine transactional need appears in Phase 6, Supabase's free tier answers it with Auth
and storage bundled — a better fit than raw Postgres would have been anyway.

## Consequences

**Positive**
- Phase 1–2 iteration is a notebook and a file — no migrations, no server, no network.
- The feature table stays portable and reproducible; `data-pipeline/` is the source of truth.
- The database is introduced against a real requirement, which makes its schema obvious
  rather than speculative.
- Free-tier idle-pause is harmless: nothing depends on the database until Phase 6, and by
  then the app is being demoed regularly.

**Negative**
- Phase 6 carries a migration task: stand up the schema, move alert-writing off files.
  Bounded — only the three transactional tables move.
- No SQL exploration over features; pandas fills that role.
- Two storage mechanisms coexist from Phase 6 (files for analytics, Postgres for state).
  This is intentional and worth stating plainly in the report: it is the standard split
  between build artifacts and application state.

**Revisit if** the feature table outgrows memory (multi-city at finer resolution), or
spatial queries become a hot path — then load features into PostGIS and query them there.
