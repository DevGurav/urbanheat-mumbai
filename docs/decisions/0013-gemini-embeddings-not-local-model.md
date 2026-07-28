# ADR-0013 — RAG embeddings via Gemini's API, not a local model

**Status:** Accepted
**Date:** 2026-07-28
**Phase:** 6

## Context

The Phase 4 RAG pipeline (`agents.md` §4) embedded documents and queries locally with
`sentence-transformers/all-MiniLM-L6-v2` on CPU — a deliberate choice at the time, stated in
`agents.md` as "never a paid embedding API." It worked without issue through Phase 5, running
on a full-RAM development machine.

Phase 6's first real Render deploy crashed on startup: the container logged
`loading artifact store…` and was killed (exit 137 — SIGKILL) a few seconds later. Reading
`backend/routers/agent.py`'s import chain confirmed the cause before touching anything:
`from backend.agents.supervisor import build_agent_layer` at module level means importing
`backend.main` — before uvicorn even binds a port — pulls in the full
`langchain → chromadb → sentence-transformers → torch` chain unconditionally.
`torch`'s runtime alone typically costs 300–500MB resident, even before any model weights
load, against Render free tier's 512MB ceiling.

## Options considered

### A — Upgrade to a paid Render tier

Keeps the local-embedding architecture untouched. Costs real money — the first paid
dependency this project would take on — and Render's Starter tier is the same 512MB as free;
Standard (2GB) would actually be needed. Rejected: this project's whole design has been
free-tier-first (ADR-0001, ADR-0002, ADR-0003, ADR-0004), and the memory problem is fixable
without spending anything.

### B — Defer the heavy import to first `/agent/chat` use, not app startup

Move `backend.agents.supervisor`'s import inside the route handler instead of the router's
module top level. This delays *when* the memory gets spent, not *how much* — `torch` still
has to load into memory the first time a real chat/RAG request arrives, at which point the
container is just as likely to be killed, mid-request instead of at boot. Rejected: trades a
loud, immediate failure for a quieter, later one; doesn't reduce peak memory at all.

### C — Gemini's embedding API instead of a local model (chosen)

Drop `sentence-transformers` and `torch` from the dependency tree entirely.
`backend/rag/ingest.py` and `retrieve.py` call `GoogleGenerativeAIEmbeddings`
(`langchain-google-genai`, already a dependency for the chat model) against
`models/gemini-embedding-001` — same `GEMINI_API_KEY` already in use, no new credential.

## Decision

**Option C.** Removed `torch`/`sentence-transformers` from `pyproject.toml` (confirmed via
`uv lock`: also drops `sympy`, `transformers`, `safetensors`, `regex`, `mpmath` — none of it
needed elsewhere). `chroma_db` was rebuilt from scratch — `gemini-embedding-001` outputs 3072
dimensions against MiniLM's 384, an incompatible change to an existing index, not additive.

**A real, disclosed cost:** each embedding call is now a live network round-trip to Gemini's
API, not local inference — ingest costs a handful of calls (batched: 28 chunks embedded in 2
`batchEmbedContents` calls, not 28), and every `/agent/chat` retrieval costs one more.
Google's per-model rate limits are not published for the free tier beyond "check AI Studio's
dashboard" — whether `gemini-embedding-001` shares a quota pool with `gemini-flash` chat
calls (the already-scarce 20 req/day, ADR-0011) or has its own separate, more generous limit
is **not confirmed**, the same honest-uncertainty position `BLUEPRINT.md`'s original
~1,500/day chat estimate was in before it was corrected by an actual 429 in production. Real
usage will reveal the true number; this is written down now so a future quota surprise has a
recorded starting hypothesis, not a mystery.

## Consequences

**Positive**
- Removes ~500MB+ of resident memory the backend never needed to keep on hand — the
  Docker image also builds faster and pulls smaller with `torch`/`transformers` gone.
- No new credential or account — same `GEMINI_API_KEY`, one fewer moving part than adding a
  paid Render tier or a third-party embedding provider would have been.

**Negative**
- Retrieval now has a live network dependency it didn't have before: a Gemini outage or
  latency spike affects `/agent/chat`'s RAG path even if the chat model call itself would
  have succeeded.
- Reverses `agents.md`'s original "never a paid embedding API" line — worth a viva panel
  asking "why," and the honest answer is exactly this ADR: it was the right call until a
  512MB deploy target proved it wasn't free, in the sense that mattered.

**Revisit if** the embedding quota turns out to share the 20 req/day chat pool and a real
demo runs into it — at that point, caching query embeddings (most repeated demo questions
already benefit from `Supervisor`'s own response cache, so this may already be moot) or a
smaller/quantized local model on a bigger paid tier become live options again, not
resurrecting `sentence-transformers` blind.
