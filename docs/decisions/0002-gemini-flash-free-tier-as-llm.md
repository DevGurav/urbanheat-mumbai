# ADR-0002 — Gemini Flash free tier as the LLM

**Status:** Accepted
**Date:** 2026-07-17
**Phase:** 0

## Context

Four agents need an LLM for intent parsing, tool calling, RAG answering and alert drafting.
The budget is ₹0 — not "cheap", zero — and no credit card is available for the project.
Traffic is: development iteration, plus a live demo where a panel asks maybe a dozen
questions. So peak concurrency is 1. The model must support reliable **function calling**,
because agents that cannot call tools cannot produce real numbers.

## Options considered

### A — Gemini Flash free tier (Google AI Studio)

**Pros** No card required; ~10 req/min and ~1,500 req/day (verified July 2026) — far above
this project's needs; solid function-calling support; first-class LangChain/LangGraph
integration via `langchain-google-genai`; large context window makes RAG stuffing simple;
same Google account as Earth Engine.
**Cons** Free tier is Flash-family only — Pro moved behind billing in May 2026; 10 req/min
is a real ceiling for a chatty multi-agent graph; free-tier data may be used for product
improvement; quotas can change with no notice.

### B — Local model via Ollama (Llama 3.1 8B / Qwen 2.5 7B)

**Pros** Genuinely free forever, no quota, no network, fully private; impressive to a reviewer.
**Cons** No GPU on the dev machine — CPU inference on a 7–8B model is seconds-to-minutes
per response, which makes a multi-step agent graph unusable; small-model function calling
is unreliable, and unreliable tool calls are indistinguishable from a broken product during
a demo; cannot deploy to Render's free tier (memory limit) so the deployed app would need a
different provider anyway, doubling the work.

### C — Groq free tier

**Pros** Extremely fast inference; free tier with no card; OpenAI-compatible API.
**Cons** Rate limits are tighter and have shifted more often; open-weight models only; less
mature function-calling behaviour than Gemini in practice.

### D — OpenAI / Anthropic paid APIs

**Pros** Best-in-class tool calling and reasoning.
**Cons** Requires a card. **Violates the hard ₹0 constraint.** Not viable regardless of
quality.

## Decision

**Gemini Flash free tier as primary, Groq as a configured fallback.**

The deciding factor is that this project's LLM load is trivially small — a demo is a dozen
requests — so the *quality and reliability* of function calling matters far more than
throughput or cost-per-token, and B's CPU-bound latency plus flaky tool calls would sink
the agent layer regardless of its philosophical appeal. Gemini clears the bar and costs
nothing. Groq is wired in behind the same interface because a single free tier is a single
point of failure on demo day, and the cost of an abstraction over two providers is one
factory function.

## Consequences

**Positive**
- Zero cost, no card, instant key from AI Studio.
- Reliable tool calling → agents can produce real model numbers rather than plausible prose.
- One Google account covers both Earth Engine and the LLM.
- Provider-agnostic wrapper means swapping models later is a config change.

**Negative**
- ~10 req/min ceiling constrains agent design: the supervisor must cap LLM hops per
  request, cache aggressively, and back off on 429s. This shapes Phase 4 from the start.
- Free-tier terms may change mid-project; a quota cut during finals is a live risk, hence
  the fallback.
- Free-tier prompts may be used for product improvement — acceptable here since all inputs
  are public geospatial data and public policy documents, no personal data. **No user PII
  may ever be sent to the LLM**; this becomes a standing rule in `agents.md`.
- Demo fragility: a rate limit during a live demo looks like a crash. Mitigated by response
  caching plus a scripted demo path warmed beforehand.

**Revisit if** the free tier is withdrawn or quotas drop below demo needs — fall back to
Groq as primary, or to Ollama for a purely local (slower) demo.
