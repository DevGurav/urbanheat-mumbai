"""Shared result shape + bounded invocation for the three tool-calling agents (Copilot,
Planning, Digital Twin). Monitoring doesn't use this — it isn't a tool-calling loop, its
trigger is deterministic code and the LLM only drafts wording (`agents.md` §7).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph

# Each tool call round-trips through two graph steps (the agent node emitting the call, the
# tool node executing it); the +2 covers the opening human turn and the closing answer turn.
# Budget-aware by construction (agents.md §8) — caps LLM hops per request on the ~10 req/min
# free tier (ADR-0002).
MAX_TOOL_CALLS = 4


@dataclass(frozen=True)
class ToolCallRecord:
    name: str
    args: dict
    result: str  # the ToolMessage content — a JSON-ish string, every tool returns a dict


@dataclass(frozen=True)
class AgentResult:
    text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


def run_agent(
    graph: CompiledStateGraph, message: str, max_tool_calls: int = MAX_TOOL_CALLS
) -> AgentResult:
    """Invoke a compiled tool-calling agent and flatten its message trace into text + the
    tool calls it made — the transparency the eventual `/agent/chat` response needs
    (api-reference.md, agents.md §1).
    """
    try:
        result = graph.invoke(
            {"messages": [("user", message)]},
            config={"recursion_limit": 2 * max_tool_calls + 2},
        )
    except GraphRecursionError:
        return AgentResult(
            text=(
                "I couldn't finish within the tool-call budget for this request. Try asking "
                "a narrower question."
            )
        )

    messages = result["messages"]
    pending_calls: dict[str, dict] = {}
    tool_calls: dict[str, ToolCallRecord] = {}
    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            for call in m.tool_calls:
                pending_calls[call["id"]] = {"name": call["name"], "args": call["args"]}
        elif isinstance(m, ToolMessage):
            call = pending_calls.get(m.tool_call_id, {"name": m.name or "unknown", "args": {}})
            tool_calls[m.tool_call_id] = ToolCallRecord(
                name=call["name"], args=call["args"], result=str(m.content)
            )

    # `.content` is not reliably a plain string: Gemini (and other providers) can return a
    # list of content blocks (`[{"type": "text", "text": "...", "extras": {...}}]`, carrying
    # e.g. a response signature) instead of `str`. `BaseMessage.text` normalizes either shape
    # to the joined text — found via a live smoke test (devlog.md), not by the mock suite,
    # since the fake model only ever returned plain strings.
    final_text = str(messages[-1].text) if messages else ""
    return AgentResult(text=final_text, tool_calls=list(tool_calls.values()))
