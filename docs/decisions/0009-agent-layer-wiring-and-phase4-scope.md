# ADR-0009 — Agent layer wiring and Phase 4 scope

**Status:** Accepted
**Date:** 2026-07-27
**Phase:** 4

## Context

Phase 3 shipped a FastAPI backend over the model, HVI and scenario engine. Phase 4 wraps
those same services as LangChain tools behind four LangGraph agents (`agents.md`). Three
coupled scope questions had to be settled before any of the four agents could be built —
they interact, so they are decided together, the same way ADR-0008 bundled Phase 2's three
coupled modelling choices.

## Options considered & decisions

### 1. Tool wiring — **direct in-process calls**

**HTTP loopback** (tools call `http://localhost:8000` like any other client) mirrors a real
microservice boundary, but means two processes must be running before the agent layer works
at all — a demo-breaking failure mode (forgetting to start the API) for no offsetting benefit
at this project's scale, plus a network hop and duplicate (de)serialization on every tool call.

**Decision: LangChain tools import `backend.store` / `data_pipeline.ml.*` directly**, in the
same process as the FastAPI app. `agents.md` §3's "one implementation, two interfaces" becomes
concrete: the store and service functions are called two ways — an HTTP router for `/city/grid`
etc., and a tool wrapper for the agents — never re-implemented for either caller.

### 2. RAG corpus — **3-document MVP subset**

`agents.md` §4 lists 6 candidate documents. Acquiring, chunking and embedding all 6 —
including a full IPCC AR6 chapter — is real work with no payoff until a demo question actually
needs that material.

**Decision: ship Mumbai Climate Action Plan + NDMA heat-wave guidelines + IMD heat-wave
criteria only.** These are the most Mumbai/India-specific and load-bearing: IMD criteria are
also what the Monitoring agent's rule-based thresholds cite (`agents.md` §7), so it serves two
purposes. WHO fact sheets, the IPCC AR6 excerpt, and other cities' Heat Action Plans remain
candidates in `references.md` §4, added later if the exit-criterion demo question needs them.
Rejected: acquiring all 6 up front, on the basis that an unused embedded document is pure cost
with no corresponding benefit before Phase 7's report needs the breadth.

### 3. Agent 2's ranking — **ΔLST × population only, no cost**

`agents.md` §5 designed Agent 2 to rank interventions by ΔLST-per-rupee × population, backed
by a curated `interventions.yaml` cost table. No cited cost-per-area figure exists in
`references.md` for either lever — Phase 3 already hit this exact gap and left `cost` out of
`POST /scenario` for the same reason (`api-reference.md`): "a cost or ΔLST figure without a
source is a fabrication" applies to cost exactly as it does to cooling coefficients.

**Decision: Agent 2 ranks by ΔLST × population affected only** for the Phase 4 exit criterion.
`estimate_cost` and `interventions.yaml` are deferred, not built, until a real cost citation is
logged. Rejected: spending kickoff time researching a citable cost figure now — this is a
literature-search task orthogonal to the agent architecture and would block Phase 4's start on
an open-ended search with no fixed time box.

## Consequences

**Positive**
- The agent layer has one code path to defend, not two (HTTP vs. in-process) —
  simpler to reason about and nothing to keep synchronized.
- The RAG and cost scope cuts are both explicit and reversible: candidates are recorded, not
  discarded, in `references.md` and `agents.md`.
- Consistent with the precedent Phase 3 already set (no invented cost figures) — the project's
  honesty rule about numbers extends unchanged into the agent layer.

**Negative**
- Agent 2's recommendations are missing the cost axis the original design (`agents.md` §5)
  called out as the ranking's second dimension — a real reduction in what "Planning Decision
  Agent" delivers this phase, not just a wording change.
- The RAG corpus is narrower than `agents.md` §4 originally scoped; a demo question that
  specifically needs WHO or IPCC material will not be answerable from retrieval until a later
  pass adds it.
- In-process wiring means the agent layer cannot be deployed or scaled independently of the
  REST API — acceptable here (ADR-0004's single-process, files-not-a-DB posture already made
  this trade for the whole backend).

**Revisit if** a cited cost-per-area figure is logged in `references.md` (restores Agent 2's
cost ranking), or a demo/report need surfaces material only in one of the deferred RAG
documents, or a future phase needs the agent layer to scale independently of the API process.
