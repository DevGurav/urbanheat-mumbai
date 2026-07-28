# Architecture Decision Records

One file per significant technical decision. Format: context → options considered →
decision → consequences.

**Rules**

- ADRs are **immutable** once committed. To reverse a decision, write a new ADR and mark
  the old one `Superseded by ADR-XXXX`.
- The one permitted edit is a **dated correction note appended at the end** — for a
  supporting *fact* that later proved wrong (a figure, a dataset detail) where the
  *decision* still stands. It never alters the original argument; it annotates it. A change
  to the decision itself always requires a new ADR, never a correction note.
- Record the decision when it is made, not after it works out. The rejected options are
  the valuable part — they are what a viva panel asks about.
- Number sequentially: `NNNN-short-kebab-title.md`.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-google-earth-engine-for-satellite-data.md) | Google Earth Engine for satellite data | Accepted |
| [0002](0002-gemini-flash-free-tier-as-llm.md) | Gemini Flash free tier as the LLM | Accepted |
| [0003](0003-drop-redis-and-websockets.md) | Drop Redis and WebSockets from the MVP | Accepted |
| [0004](0004-files-first-supabase-later.md) | Files first, Supabase later | Accepted |
| [0005](0005-land-surface-temperature-as-target.md) | Land Surface Temperature as the model target | Accepted |
| [0006](0006-gradient-boosted-trees-over-deep-learning.md) | Gradient-boosted trees over deep learning | Accepted |
| [0007](0007-200m-analysis-grid.md) | 200 m analysis grid | Accepted |
| [0008](0008-spatial-cv-and-leakage-policy.md) | Spatial CV, training set, and feature policy | Accepted |
| [0009](0009-agent-layer-wiring-and-phase4-scope.md) | Agent layer wiring and Phase 4 scope | Accepted |
| [0010](0010-monitoring-agent-heatwave-rule.md) | Monitoring agent's heat-wave trigger rule | Accepted |
| [0011](0011-drop-groq-fallback.md) | Drop the Groq fallback for the Phase 4 MVP | Accepted |
| [0012](0012-alerts-stay-file-based.md) | Alerts stay file-based, not Supabase | Accepted |

## Template

```markdown
# ADR-NNNN — Title

**Status:** Proposed | Accepted | Superseded by ADR-XXXX
**Date:** YYYY-MM-DD
**Phase:** N

## Context
What forced a decision? Constraints in play.

## Options considered
### A — name
Pros / cons.
### B — name
Pros / cons.

## Decision
What was chosen, and the deciding factor.

## Consequences
**Positive** / **Negative** / **Revisit if…**
```
