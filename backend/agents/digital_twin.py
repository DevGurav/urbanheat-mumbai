"""Agent 3 — Digital Twin Simulation: natural language → structured scenario → engine →
narration (`agents.md` §6, canonical numbering ADR-0009).
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from backend.agents.llm import get_llm
from backend.agents.prompts import DIGITAL_TWIN_SYSTEM_PROMPT
from backend.agents.tools import build_toolbelt
from backend.store import Store

TOOL_NAMES = ("simulate_scenario", "get_cell_stats", "explain_ward")


def build_digital_twin(store: Store, llm: BaseChatModel | None = None) -> CompiledStateGraph:
    tools = [tool for tool in build_toolbelt(store) if tool.name in TOOL_NAMES]
    return create_agent(
        llm or get_llm(), tools, system_prompt=DIGITAL_TWIN_SYSTEM_PROMPT, name="digital_twin"
    )
