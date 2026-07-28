-- UrbanHeat AI — Supabase schema (Phase 6, ADR-0004, ADR-0012, PROGRESS.md kickoff).
--
-- One table. `saved_scenarios` is the only genuinely per-user, transactional data this
-- project has — everything else (features, model, SHAP, alerts) is a regenerable build
-- artifact and stays a file (ADR-0004, ADR-0012). No custom `profiles` table either:
-- Supabase Auth's own `auth.users` is enough, since nothing here needs extra profile fields.
--
-- Stores the scenario CONFIG only, not a computed result (Phase 6 kickoff, PROGRESS.md):
-- loading a saved scenario re-calls POST /scenario, so what a user sees is always freshly
-- computed against the current model and data, never a stale snapshot that silently drifted
-- from a retrained model.
--
-- Run this once, in the Supabase dashboard's SQL editor, after creating the project
-- (docs/runbook.md §1.4). Idempotent — safe to re-run.

create table if not exists saved_scenarios (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  -- Mirrors backend/schemas.py's ScenarioRequest exactly — same two interventions, same
  -- coverage range — so a row here can never describe a scenario the backend would reject.
  ward_code text not null,
  intervention text not null check (intervention in ('greening', 'cool_roof')),
  coverage double precision not null default 1.0 check (coverage >= 0 and coverage <= 1),
  saved_at timestamptz not null default now()
);

create index if not exists saved_scenarios_user_id_idx on saved_scenarios (user_id);

alter table saved_scenarios enable row level security;

-- A user sees, saves, and removes only their own scenarios — the one place this project
-- holds per-user data. Every read endpoint elsewhere (map, analytics, chat, alerts) stays
-- open and unauthenticated (api-reference.md: "Auth ... on write endpoints from Phase 6").
-- No update policy: the task this schema serves is save/list/delete, not edit-in-place
-- (PROGRESS.md's Phase 6 board) — add one only if a real need for it shows up.

create policy "select own scenarios" on saved_scenarios
for select
  using (auth.uid () = user_id);

create policy "insert own scenarios" on saved_scenarios
for insert
with
  check (auth.uid () = user_id);

create policy "delete own scenarios" on saved_scenarios
for delete using (auth.uid () = user_id);
