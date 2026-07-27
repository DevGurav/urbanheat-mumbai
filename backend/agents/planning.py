"""Agent 2 — Planning Decision: hotspots → SHAP → simulate → rank by delta-LST × population
(`agents.md` §5, canonical numbering ADR-0009).

No cost field or `estimate_cost` tool — descoped at the Phase 4 kickoff (ADR-0009): no cited
cost-per-area figure exists yet in `references.md`, the same gap Phase 3 hit on `/scenario`.
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from backend.agents.llm import get_llm
from backend.agents.prompts import PLANNING_SYSTEM_PROMPT
from backend.agents.tools import build_toolbelt
from backend.store import Store

TOOL_NAMES = ("get_hotspots", "explain_ward", "simulate_scenario")


def build_planning_agent(store: Store, llm: BaseChatModel | None = None) -> CompiledStateGraph:
    tools = [tool for tool in build_toolbelt(store) if tool.name in TOOL_NAMES]
    return create_agent(
        llm or get_llm(), tools, system_prompt=PLANNING_SYSTEM_PROMPT, name="planning"
    )
