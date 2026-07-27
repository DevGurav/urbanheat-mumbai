"""Agent 1 — Urban AI Copilot: RAG + data tools (`agents.md` §4, canonical numbering ADR-0009).

Role: answer planner questions over city data and policy documents. Tools: every toolbelt
entry except `simulate_scenario` — that lever belongs to the Digital Twin (`agents.md` §6),
not the Copilot, which reads and explains rather than simulates.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from backend.agents.llm import get_llm
from backend.agents.prompts import COPILOT_SYSTEM_PROMPT
from backend.agents.tools import build_toolbelt
from backend.rag.retrieve import Retriever
from backend.store import Store


def build_copilot(
    store: Store, retriever: Retriever, llm: BaseChatModel | None = None
) -> CompiledStateGraph:
    """`retriever` is required, not optional (unlike `build_toolbelt`'s default) — a Copilot
    without `search_knowledge` isn't the agent `agents.md` §4 describes, so it fails at
    construction rather than silently shipping without its defining capability.
    """
    tools = [
        tool
        for tool in build_toolbelt(store, retriever=retriever)
        if tool.name != "simulate_scenario"
    ]
    return create_agent(
        llm or get_llm(), tools, system_prompt=COPILOT_SYSTEM_PROMPT, name="copilot"
    )
