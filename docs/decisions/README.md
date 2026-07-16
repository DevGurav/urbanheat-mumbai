# Architecture Decision Records

One file per significant technical decision. Format: context → options considered →
decision → consequences.

**Rules**

- ADRs are **immutable** once committed. To reverse a decision, write a new ADR and mark
  the old one `Superseded by ADR-XXXX`.
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
