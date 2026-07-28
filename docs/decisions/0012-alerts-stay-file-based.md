# ADR-0012 — Alerts stay file-based, not Supabase

**Status:** Accepted
**Date:** 2026-07-28
**Phase:** 6

## Context

ADR-0004 scoped three tables for Supabase in Phase 6: users, saved scenarios, and alert
history. That decision was made in Phase 0, before any of the three existed — a reasonable
guess at the time, but a guess. Alerts have since been built (Phase 4): a file-based dedupe
log (`backend/agents/alerts.py`'s `alerts.jsonl`), written once a day by a GitHub Actions
cron, read by `GET /alerts` and rendered by `src/sections/Alerts.tsx`. With the real shape of
the data now known, the Phase 6 kickoff revisits whether it actually belongs in Postgres.

This is a **partial** revision of ADR-0004, not a reversal — users and saved scenarios still
move to Supabase exactly as ADR-0004 scoped. Only alert history's disposition changes.

## Options considered

### A — Move alerts to Supabase now (ADR-0004 as originally written)

**Pros** One consistent storage story for everything Phase 6 touches; no mixed file+DB split
to explain later.
**Cons** Real migration work for no new capability: `GET /alerts` already works correctly
against the file. The cron would need to write to Postgres instead (a new failure mode —
Render's free tier and Supabase's free tier pausing independently is two idle-pause risks to
reason about instead of one), and RLS doesn't apply here anyway, since alerts are public
read data for everyone, not per-user state.

### B — Keep alerts file-based (chosen)

**Pros** Alerts turn out to fit ADR-0004's own **first** category — "analytical, read-only,
regenerable" — not its second. They are city-wide, public, written by an automated process,
never mutated by a user, and trivially regenerable (re-run the check). That is a build
artifact's profile, the same as `features.parquet`, not a transactional record like an
account or a saved scenario. No user ever owns or edits an alert.
**Cons** The project now has two persistence stories from Phase 6 onward (files for
analytics-shaped data including alerts, Postgres for user-shaped data) instead of the one
ADR-0004 anticipated. Worth stating plainly, not glossing over — see Consequences.

## Decision

**Option B.** Alerts stay exactly where Phase 4 put them: a file, written by the GitHub
Actions cron via `backend/agents/alerts.py`, served by `GET /alerts`. `users` and
`saved_scenarios` move to Supabase in Phase 6 as ADR-0004 already decided; that part is
unchanged.

## Consequences

**Positive**
- No migration work for a table that was never actually the kind of data ADR-0004's
  "transactional" category was written for — closing a real gap between the Phase 0 guess
  and the Phase 4 reality, not deferring work.
- Removes a second idle-pause risk (Supabase pausing a cron-fed table) from the deployment
  story for no capability gained.

**Negative**
- Two persistence mechanisms coexist from Phase 6 on: files for regenerable/public data
  (features, models, alerts), Postgres for per-user transactional data (accounts, saved
  scenarios). This is the same split ADR-0004 already named as intentional for the first two
  — alerts simply turned out to belong on that side of the line too, not a new kind of split.

**Revisit if** alerts ever become per-user (e.g., a "subscribe to alerts for my ward"
feature) — that would be genuinely transactional state and belong in Postgres, unlike the
current city-wide broadcast feed.
