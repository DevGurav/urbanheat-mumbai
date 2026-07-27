"""The supervisor: one classification call routes a chat message to one of the three
conversational agents (`agents.md` §2). Monitoring is not part of this routing — it is
triggered by the cron job (`agents.md` §7, "scheduled"), never by a user message.

"Routing is a single classification call, not a negotiation between agents" (`agents.md` §2)
— chattier multi-agent patterns burn the rate limit for no gain at this scale (ADR-0002).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel

from backend.agents.copilot import build_copilot
from backend.agents.digital_twin import build_digital_twin
from backend.agents.llm import get_llm
from backend.agents.planning import build_planning_agent
from backend.agents.result import AgentResult, ToolCallRecord, run_agent
from backend.rag.retrieve import Retriever
from backend.store import Store

AgentName = Literal["copilot", "planning", "digital_twin"]

ROUTING_PROMPT = """Classify which specialist agent should handle this message. Reply with \
exactly one word, no punctuation: copilot, planning, or digital_twin.

- copilot: questions about where or why it is hot, city data, or policy documents — e.g. \
"where is it hottest", "why is Kurla warm", "what does the climate plan say about heat"
- planning: questions asking what to do or which intervention to prioritise — e.g. "what \
should we do about ward L", "rank interventions for the hottest wards"
- digital_twin: what-if / scenario questions about a specific intervention — e.g. "what if \
we plant trees in Kurla", "simulate cool roofs in ward A"

Message: {message}"""


@dataclass(frozen=True)
class ChatResult:
    agent: AgentName
    text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


class Supervisor:
    """Built once per app lifetime, the same posture as `backend.store.Store` (ADR-0004) — the
    three agent graphs and the router's LLM binding are constructed once, not per request.
    """

    def __init__(self, store: Store, retriever: Retriever, llm: BaseChatModel | None = None):
        base_llm = llm or get_llm()
        self._router_llm = base_llm
        self._agents = {
            "copilot": build_copilot(store, retriever, llm=base_llm),
            "planning": build_planning_agent(store, llm=base_llm),
            "digital_twin": build_digital_twin(store, llm=base_llm),
        }

    def route(self, message: str) -> AgentName:
        response = self._router_llm.invoke(ROUTING_PROMPT.format(message=message))
        choice = str(response.content).strip().lower()
        if choice in self._agents:
            return choice  # type: ignore[return-value]
        return "copilot"  # an unparseable classification falls back to the general Q&A agent,
        # not a guess at the user's intent — copilot's own guardrails still apply from there

    def handle(self, message: str) -> ChatResult:
        agent_name = self.route(message)
        result: AgentResult = run_agent(self._agents[agent_name], message)
        return ChatResult(agent=agent_name, text=result.text, tool_calls=result.tool_calls)


def build_agent_layer(store: Store, tool_calls: list[ToolCallRecord]) -> dict | None:
    """If the agent called `simulate_scenario`, build the same kind of GeoJSON layer
    `/city/grid` serves, scoped to just the cells that scenario touched — the "optional GeoJSON
    layer" `api-reference.md` promises for `/agent/chat`. Any other tool call (or none) has
    nothing mappable, so this returns `None` rather than inventing a layer.
    """
    for call in tool_calls:
        if call.name != "simulate_scenario":
            continue
        payload = json.loads(call.result)
        if "error_code" in payload:
            continue  # a failed scenario call has no cells to map
        dlst_by_cell = {c["cell_id"]: c["dlst"] for c in payload["cells"]}
        frame = store.features[store.features["cell_id"].isin(dlst_by_cell)][
            ["cell_id", "geometry"]
        ].copy()
        frame["dlst"] = frame["cell_id"].map(dlst_by_cell).round(3)
        frame["geometry"] = frame.geometry.simplify(0.0001, preserve_topology=True)
        return json.loads(frame.to_json())
    return None
