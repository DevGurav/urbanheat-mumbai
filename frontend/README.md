# UrbanHeat AI — frontend

React + TypeScript + Vite + MUI dashboard over the Phase 3–4 backend (`../backend/`). See
[`../docs/architecture.md`](../docs/architecture.md) and
[`../docs/api-reference.md`](../docs/api-reference.md) for the contracts this consumes.

## Setup

```bash
npm install
cp ../.env.example .env.local   # or set VITE_API_BASE_URL directly
npm run dev                     # → http://localhost:5173
```

The backend (`uv run uvicorn backend.main:app --reload`) must be running at
`VITE_API_BASE_URL` (default `http://localhost:8000`) for anything beyond the app shell to
render real data.

## Structure

- `src/api/types.ts` — hand-written TypeScript mirrors of `backend/schemas.py` (Phase 5
  kickoff decision, `PROGRESS.md` — not generated from `/openapi.json`)
- `src/api/client.ts` — one typed `fetch` wrapper function per backend endpoint
- `src/api/hooks.ts` — one TanStack Query hook per endpoint the UI calls
- `src/sections/` — the five dashboard sections (heat map, analytics, scenario simulator,
  Copilot chat, alerts feed), switched by `App.tsx`, not routed (no router — a single internal
  dashboard, no shareable per-section URLs needed)

## Conventions

Strict TypeScript (`tsconfig.app.json`'s `strict: true`); no `any` without a comment
justifying it (`../docs/conventions.md`). `npm run lint` (oxlint) and `npx tsc -b` should both
be clean before a commit.
