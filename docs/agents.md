# Agents

Roles, tools, guardrails and prompt design for the LangGraph layer.

**Status:** design (Phase 4). Prompts and tool signatures are drafts — updated as built.

---

## 1. Design principles

**The LLM decides *what*, never computes *what*.** Every number a user sees comes from the
model, the scenario engine or a dataset — never from the LLM's own estimate. The LLM parses
intent, picks tools, and narrates results. If an agent ever states a temperature or a cost
that did not come from a tool call, that is a bug of the most serious kind.

**Tools are a typed allowlist.** The LLM chooses arguments; Pydantic validates them; the
function executes. No arbitrary code, no SQL generation, no shell.

**Budget-aware by construction.** ~10 requests/min on the Gemini free tier (ADR-0002) means
LLM hops per user request are capped, answers are cached, and 429s trigger backoff then a
Groq fallback.

**Fail loudly, never plausibly.** A tool that errors must produce "I couldn't compute that",
not an LLM-invented number. Plausible fabrication is the worst failure mode this system has.

---

## 2. Supervisor graph

```mermaid
flowchart TB
    IN[User message] --> SUP{{Supervisor<br/>route by intent}}
    SUP -->|"where/why is it hot"| A1[1 · Copilot]
    SUP -->|"what should we do"| A2[2 · Planning]
    SUP -->|"what if"| A3[3 · Digital Twin]
    SUP -->|scheduled| A4[4 · Monitoring]
    A1 & A2 & A3 --> OUT[Response + optional map layer]
    A4 --> FEED[(Alerts feed)]
```

Routing is a single classification call, not a negotiation between agents — chattier
multi-agent patterns burn the rate limit for no gain at this scale.

**Numbering note.** Earlier drafts of this diagram and `architecture.md`'s Components diagram
numbered the agents in build order (1 Planning, 2 Digital Twin, 3 Monitoring, 4 Copilot),
while this file's own §4–§7 headers and `PROGRESS.md` numbered them in exit-criterion order
(1 Copilot, since it's the agent the Phase 4 exit criterion tests). Canonicalized on the
latter at the Phase 4 kickoff (ADR-0009) — both diagrams now match §4–§7 below.

---

## 3. Shared toolbelt

Thin wrappers over Phase 3 services, called **in-process** — a LangChain tool imports
`backend.store` / `data_pipeline.ml.*` directly rather than calling the REST API over HTTP
(ADR-0009). Same functions the REST API exposes — one implementation, two interfaces: an
HTTP router for `/city/grid` etc., a tool wrapper for the agents, never a re-implementation
of either.

| Tool | Signature | Returns |
|---|---|---|
| `get_hotspots` | `(n: int = 10, by: "hvi" \| "lst" = "hvi")` | Ranked wards/cells with values |
| `get_cell_stats` | `(cell_id: int)` | Feature vector + LST + ward |
| `explain_cell` | `(cell_id: int)` | SHAP attribution, °C per driver |
| `explain_ward` | `(ward: str)` | Aggregated SHAP + summary stats |
| `simulate_scenario` | `(ward: str \| cell_ids: list, intervention: str, coverage: float)` | ΔLST per cell, summary, clamp warnings |
| ~~`estimate_cost`~~ | `(intervention: str, area_m2: float)` | **Deferred (ADR-0009)** — no cited cost-per-area figure exists yet in `references.md`; build once one is logged |
| `get_weather` | `(days: int = 7)` | Open-Meteo forecast |
| `get_trend` | `(ward: str \| None)` | LST trend °C/yr |
| `search_knowledge` | `(query: str, k: int = 4)` | Policy-document passages + sources |

Every tool returning a number also returns its **provenance** (dataset, model version, or
document + page) so the agent can cite rather than assert.

---

## 4. Agent 1 — Urban AI Copilot (RAG + data)

**Role** Answer planner questions over city data and policy documents.
**Tools** All read tools + `search_knowledge`.

**RAG corpus** (`data/knowledge_base/`) — **Phase 4 MVP (ADR-0009):** Mumbai Climate Action
Plan · NDMA heat-wave guidelines · IMD heat-wave criteria (also what the Monitoring agent's
thresholds cite, §7). **Later candidates**, not built this phase: WHO heat-health fact
sheets, IPCC AR6 urban excerpts, other cities' Heat Action Plans — added if a demo or report
need surfaces material only they contain. All public documents; sources listed in
`references.md` §4.

**Retrieval** ChromaDB embedded · `sentence-transformers/all-MiniLM-L6-v2` on CPU
(never a paid embedding API) · ~800-token chunks, 100 overlap · top-k 4.

**Guardrails**
- Answers about *the city* come from tools. Answers about *policy* come from retrieval with
  citations. Never blend the two silently.
- Retrieval miss → say so. Do not fall back to the model's own knowledge of Mumbai.
- Always distinguish measured (LST), modelled (predicted, simulated) and cited (documents).

*Draft system prompt*
> You are an urban-heat analyst for Greater Mumbai. Answer only from tool results and
> retrieved passages. Never estimate a temperature, cost or ranking yourself — call a tool.
> All temperatures are **surface** temperatures from satellite thermal imagery at ~10:30
> local time, not air temperature; say so when it matters. Cite the dataset or document
> behind every number. If tools and retrieval cannot answer, say you don't know.

## 5. Agent 2 — Planning Decision Agent

**Role** Turn hotspots into ranked intervention plans.
**Tools** `get_hotspots`, `explain_ward`, `simulate_scenario`.

**Method** Rank by HVI → read SHAP to find *why* each ward is hot → choose interventions
that target the actual driver (low NDVI → planting; high albedo deficit → cool roofs) →
simulate → rank by ΔLST × population affected.

**Cost ranking deferred (ADR-0009).** The original design costed each recommendation via a
curated `interventions.yaml` table and ranked by ΔLST per rupee. No cited cost-per-area figure
exists yet in `references.md` — the same gap Phase 3 hit and left `cost` out of `/scenario`
for (`api-reference.md`). Build `estimate_cost` and `interventions.yaml` once a real citation
is logged; until then, the LLM never invents a coefficient, so the tool does not exist rather
than existing with a placeholder.

**Guardrails** Every recommendation carries ΔLST (modelled), the SHAP driver that motivated
it, and the correlational caveat from `ml-methodology.md` §6. No cost figure is stated —
silence here is preferable to an invented number.

## 6. Agent 3 — Digital Twin Simulation Agent

**Role** Natural language → structured scenario → engine → narration.
**Tools** `simulate_scenario`, `get_cell_stats`, `explain_ward`.

**Flow** "What if we plant trees across 20% of Kurla?" → `{ward: "Kurla", intervention:
"tree_planting", coverage: 0.2}` → engine → "≈1.8 °C mean surface cooling across 340 cells;
strongest where NDVI is currently lowest."

**Guardrails**
- Ambiguous input → ask, don't guess. An unstated coverage fraction is not 100%.
- Clamped scenarios (§6, `ml-methodology.md`) must **say** they were clamped.
- Phrase results as analogy, never causation: "cells like this but greener run ~1.8 °C
  cooler" — not "this will cool Kurla by 1.8 °C".

## 7. Agent 4 — Autonomous Monitoring Agent

**Role** Daily heatwave watch → alerts feed.
**Trigger** GitHub Actions cron (ADR-0003 — no Redis queue), ~06:00 IST.
**Tools** `get_weather`, `get_hotspots`, `explain_ward`.

**Logic — thresholds are rule-based, not LLM-judged.** IMD-style criteria (plains: max
≥40 °C, or ≥4.5 °C above normal) evaluated in code. The LLM only *drafts the wording* of
an alert whose trigger has already fired deterministically. An LLM deciding whether a
heatwave exists would be both unreliable and indefensible.

**Output** Alert row: severity, wards affected (forecast ∩ high HVI), drafted summary,
timestamp. Written to file (Phase 4) → Supabase (Phase 6). Optional email via Gmail SMTP.

**Guardrails** Dedupe — one alert per event, not per run. Cap emails per day. Alerts state
that they are model-derived and advisory, not an official IMD warning. This system is not
an authority and must never imply it is.

---

## 8. Rate-limit strategy

The real number, measured live (devlog.md, 2026-07-27): **20 requests/day** for this project's
Gemini free tier, not the ~1,500/day originally assumed. That makes the cache the load-bearing
row in this table, not an optimisation.

| Layer | Approach | Status |
|---|---|---|
| Cap hops | Supervisor routes once; agents get a bounded tool-call loop (`MAX_TOOL_CALLS=4`) | ✅ built |
| Cache | `(question, data_version)` → response; identical demo questions cost nothing, TTL 24h | ✅ built (`Supervisor`) |
| Backoff | Exponential retry on 429 | ✅ built — `ChatGoogleGenerativeAI`'s own retry, `max_retries=3` set explicitly (`backend/agents/llm.py`), not left at the library default |
| Fallback | ~~`GROQ_API_KEY` set → retry there on repeated 429~~ | ❌ **dropped (ADR-0011)** — one credential to manage, not two; the cache covers the practical case (repeat demo questions) a fallback mainly protected against |
| Warm demos | Pre-run the scripted demo questions so answers are cached | runbook.md |

**Not a defence — a warning.** A live viva demo hitting a rate limit looks like a crash, and
without a fallback (ADR-0011) a fully exhausted daily quota has no recovery until it resets.
The cache-warming step before any demo is a runbook item, not an optimisation.

---

## 9. Safety & privacy

- **No PII to the LLM, ever** (ADR-0002 — free-tier prompts may be used for product
  improvement). Inputs are public geospatial data and public documents only.
- User chat text is untrusted; it reaches tools only as Pydantic-validated arguments.
- Prompt injection surface: retrieved documents. Chunks are data, not instructions — the
  system prompt states that retrieved text is never to be followed as a command.
- Outputs are advisory. The dashboard footer says the system is a decision-support
  prototype, not an official heat advisory.
