# ADR-0011 — Drop the Groq fallback for the Phase 4 MVP

**Status:** Accepted
**Date:** 2026-07-27
**Phase:** 4

## Context

ADR-0002 chose Gemini Flash as the LLM and named a Groq fallback as part of the mitigation for
the free tier's rate limit; `agents.md` §8's rate-limit strategy table lists it alongside
caching and backoff. Building it means requesting a second free-tier credential
(`GROQ_API_KEY`, console.groq.com) and adding a provider-switch path in `backend/agents/llm.py`
that retries a failed Gemini call against `langchain-groq` instead.

This surfaced as a real decision, not a hypothetical one, immediately after the Phase 4 agents
went live: a real `429` was hit during live verification (devlog.md, 2026-07-27), and Google's
own error response named the actual limit — **20 requests/day** for this project, not the
~1,500/day `BLUEPRINT.md` had documented. That number sharpens exactly the question a fallback
is meant to answer: is a second provider worth managing for this project's actual usage
pattern (a solo-developer demo, not production traffic)?

## Options considered

### A — Build the Groq fallback now

Matches the original `agents.md` §8 plan. Cost: a second account/credential to create and
keep valid, a provider-switch code path to write and test (different response shape, likely
its own quirks — the two real bugs found in this same session, both about response-content
shape, are a fresh reminder that "just swap the model" is rarely actually just swapping the
model), and a second thing that can silently break (this session's entire Gemini-key saga is
itself a demonstration of how much a single credential can go wrong).

### B — Drop it; rely on caching + backoff (chosen)

Author's call, asked directly and confirmed: manage one credential, not two. The response
cache (`Supervisor`'s `(question, data_version)` cache, this same session) already answers the
scenario the fallback was mainly protecting against — a live demo re-asking the same scripted
questions. `ChatGoogleGenerativeAI`'s own retry/backoff (`backend/agents/llm.py`) absorbs
genuine transient blips. What a fallback uniquely covers — the daily quota being *fully*
exhausted mid-demo on a genuinely novel question — is judged an acceptable residual risk for a
solo academic project's demo, not a production system with real users depending on uptime.

## Decision

**Option B.** `get_llm()` only ever returns a Gemini-backed model. `GROQ_API_KEY` stays in
`.env.example` as a documented-but-unused optional field (harmless to leave; costs nothing to
delete either). `/agent/chat`'s `agent_upstream_unavailable` 503 (`backend/routers/agent.py`)
is the honest failure mode when the daily quota is exhausted — a clean, labelled unavailability,
not a silent hang or a fabricated answer.

## Consequences

**Positive**
- One credential to manage, one provider's response shape to defend, one fewer
  moving part in the demo-day failure surface.
- The cache is the change that actually matters for the scenario a fallback would have
  covered in practice (repeat questions during a demo) — building both would have been
  redundant effort for the same practical benefit.

**Negative**
- A demo that exhausts the real 20/day quota on genuinely novel questions has no fallback —
  `/agent/chat` 503s for the rest of the day. `runbook.md`'s pre-demo cache-warming step exists
  specifically to make this unlikely during an actual presentation, not to eliminate the risk.
- `agents.md` §8's rate-limit table now overstates what is built; corrected alongside this ADR.

**Revisit if** a future phase needs uptime guarantees a single free-tier provider can't offer
(Phase 6 public deployment is the obvious candidate) — at that point `GROQ_API_KEY` already
being scaffolded in `.env.example` means the fallback is a contained addition, not a redesign.
