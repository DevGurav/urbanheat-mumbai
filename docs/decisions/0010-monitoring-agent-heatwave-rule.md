# ADR-0010 — Monitoring agent's heat-wave trigger rule

**Status:** Accepted
**Date:** 2026-07-27
**Phase:** 4

## Context

`agents.md` §7 requires the Monitoring agent's trigger to be rule-based, evaluated in code —
"the LLM only drafts the wording of an alert whose trigger has already fired
deterministically." The rule was meant to be IMD's official Heat Wave criteria (`references.md`
§4, `data/knowledge_base/imd_faq_heatwave.txt`, extracted primary-source at the Phase 4 RAG
kickoff).

IMD's actual criteria for a **coastal station** — Mumbai is one — are two-part: an absolute
threshold (actual maximum ≥37 °C) **and** a departure of ≥4.5 °C from the station's
climatological normal maximum temperature. This project has no real IMD normal to depart
from. The closest thing in the pipeline is `data_pipeline/sources/weather.py`'s Mar–May
multi-year *mean* air temperature — and that stage's own finding, stated in its own docstring,
is that the value is near-constant across the city (~0.6 °C spread) and was flagged in Phase 1
as a feature-selection drop candidate for having near-zero signal. Stretching it into an IMD
"normal maximum temperature" would misrepresent both what IMD's criteria mean and what this
project's own data supports.

## Options considered

### A — Full departure-based rule using the ERA5 dry-season mean as "normal"

Fires more often — a more demonstrable Monitoring agent. Rejected: it answers "how does this
project's own weather mean compare to itself" dressed up as "IMD's official criteria," which
is not defensible as **the exact definition used** (`agents.md` §7's own phrasing) and is
exactly the kind of plausible-looking invented precision `conventions.md` calls the worst
defect this system can ship.

### B — Absolute-threshold-only rule (chosen)

Use only the IMD criteria that need no baseline: Heat Wave at forecast max ≥45 °C, Severe Heat
Wave ≥47 °C (IMD FAQ, option "b" — Based on Actual Maximum Temperature). Add a lower-severity
"advisory" tier at ≥37 °C — Mumbai's coastal base threshold — explicitly labelled as *not* a
full IMD declaration, since the departure-from-normal half of that specific rule is unverified.

## Decision

**Option B.** `backend/agents/monitoring.py`'s `_severity()` checks the Open-Meteo forecast
max temperature (`services.get_weather`) against three real, cited, primary-source IMD
numbers — 37 / 45 / 47 °C — and returns `None` (no trigger, no alert) otherwise. Every alert
carries a caveat stating plainly that this is a threshold-only approximation of IMD's full
criteria, not an official warning — consistent with `agents.md` §7's existing "advisory, not
an official IMD warning" guardrail, which already covers exactly this gap.

## Consequences

**Positive**
- Every number the Monitoring agent acts on traces to a primary source (`references.md` §4),
  with no invented or misapplied "normal" temperature.
- The caveat is not a new admission bolted on afterward — it is `agents.md`'s own pre-existing
  guardrail, applied to the one case it was written for.

**Negative**
- The agent will rarely trigger for Mumbai in practice — 45 °C+ forecast highs are uncommon at
  a coastal station. A live demo may need a manually lowered threshold or a mocked forecast to
  show the alert path at all; the underlying rule stays real.
- The lower advisory tier (≥37 °C) is real IMD terminology (Mumbai's coastal base threshold)
  but not a full IMD Heat Wave declaration — worth restating clearly in any UI that surfaces
  it, so "advisory" is never read as "IMD confirmed this."

**Revisit if** a real climatological normal for Mumbai (IMD's own published 1991–2020 or
similar normals) becomes available, at which point the full two-part coastal rule (Option A's
shape, with a real baseline instead of the ERA5 mean) can replace this one without changing
the trigger's plumbing — only `_severity()`'s inputs change.
