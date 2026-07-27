"""The four Phase 4 agents (`agents.md` §4–§7), tested without a live LLM: a small local fake
chat model exercises the real tool-calling loop end-to-end (real tools, real store, real
graph), so `run_agent`'s tool-call extraction and each agent's tool wiring are genuinely
verified. `GEMINI_API_KEY` is a separate, real-network smoke test (not in this suite,
devlog.md) — ADR-0009's in-process wiring is what's under test here, not Gemini itself.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FakeToolCallingModel(BaseChatModel):
    """A scripted chat model: returns each of `responses` in order, one per `.invoke()`/graph
    step. `bind_tools` is a no-op that returns `self` — the fake doesn't need real tool
    schemas to decide what to call, since the response sequence is pre-scripted.
    """

    responses: list[AIMessage] = []
    _i: int = 0

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        response = self.responses[self._i]
        self._i += 1
        return ChatResult(generations=[ChatGeneration(message=response)])

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling"


def _tool_names(graph) -> set[str]:
    # `_tools_by_name` is a private field of langgraph's ToolNode — the only way to inspect a
    # compiled graph's bound tools without invoking it. If a langgraph upgrade removes it,
    # this test fails loudly, which is the right outcome for a coupling like this.
    return set(graph.nodes["tools"].bound._tools_by_name)


@pytest.fixture
def store():
    from backend.store import load_store

    try:
        return load_store()
    except FileNotFoundError as exc:
        pytest.skip(f"artifacts not built: {exc}")
    except Exception as exc:  # noqa: BLE001 - a missing .env should skip, not error
        if ".env" in str(exc) or "config" in str(exc).lower():
            pytest.skip(str(exc))
        raise


@pytest.fixture
def retriever(settings):
    from backend.rag.retrieve import Retriever

    try:
        return Retriever(chroma_dir=settings.chroma_dir)
    except FileNotFoundError as exc:
        pytest.skip(f"Chroma index not built: {exc}")


# --- tool wiring per agent --------------------------------------------------------------------


def test_copilot_has_every_tool_except_simulate_scenario(store, retriever):
    from backend.agents.copilot import build_copilot

    fake = FakeToolCallingModel(responses=[AIMessage(content="hi")])
    graph = build_copilot(store, retriever, llm=fake)
    names = _tool_names(graph)
    assert "simulate_scenario" not in names
    assert "search_knowledge" in names
    assert names == {
        "get_hotspots",
        "get_cell_stats",
        "explain_cell",
        "explain_ward",
        "get_weather",
        "get_trend",
        "search_knowledge",
    }


def test_planning_agent_has_exactly_its_three_tools(store):
    from backend.agents.planning import build_planning_agent

    fake = FakeToolCallingModel(responses=[AIMessage(content="hi")])
    graph = build_planning_agent(store, llm=fake)
    assert _tool_names(graph) == {"get_hotspots", "explain_ward", "simulate_scenario"}


def test_digital_twin_has_exactly_its_three_tools(store):
    from backend.agents.digital_twin import build_digital_twin

    fake = FakeToolCallingModel(responses=[AIMessage(content="hi")])
    graph = build_digital_twin(store, llm=fake)
    assert _tool_names(graph) == {"simulate_scenario", "get_cell_stats", "explain_ward"}


# --- run_agent: the real tool-calling loop end-to-end, real tools, fake LLM -------------------


def test_run_agent_executes_a_real_tool_and_reports_it(store):
    from backend.agents.digital_twin import build_digital_twin
    from backend.agents.result import run_agent

    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "explain_ward",
                    "args": {"ward_code": "A", "top": 2},
                    "id": "call_1",
                }
            ],
        ),
        AIMessage(content="Ward A is warm because of X and Y."),
    ]
    fake = FakeToolCallingModel(responses=responses)
    graph = build_digital_twin(store, llm=fake)
    result = run_agent(graph, "why is ward A hot?")

    assert result.text == "Ward A is warm because of X and Y."
    assert len(result.tool_calls) == 1
    call = result.tool_calls[0]
    assert call.name == "explain_ward"
    assert call.args == {"ward_code": "A", "top": 2}
    assert "ward_code" in call.result  # the real explain_ward JSON, not a stub


def test_run_agent_reports_no_tool_calls_when_the_model_answers_directly(store):
    from backend.agents.planning import build_planning_agent
    from backend.agents.result import run_agent

    fake = FakeToolCallingModel(responses=[AIMessage(content="I need more information.")])
    graph = build_planning_agent(store, llm=fake)
    result = run_agent(graph, "help")

    assert result.text == "I need more information."
    assert result.tool_calls == []


def test_run_agent_surfaces_a_labelled_tool_error_not_a_crash(store):
    """A tool returning {error, error_code} (backend/agents/tools.py's _safe_call) should
    reach run_agent as an ordinary ToolMessage — the agent sees the error text like any other
    result, rather than the graph raising.
    """
    from backend.agents.digital_twin import build_digital_twin
    from backend.agents.result import run_agent

    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "get_cell_stats", "args": {"cell_id": 999999999999}, "id": "call_1"}
            ],
        ),
        AIMessage(content="I couldn't find that cell."),
    ]
    fake = FakeToolCallingModel(responses=responses)
    graph = build_digital_twin(store, llm=fake)
    result = run_agent(graph, "stats for a bad cell id")

    assert result.tool_calls[0].name == "get_cell_stats"
    assert "cell_not_found" in result.tool_calls[0].result


def test_run_agent_stops_within_budget_on_a_runaway_loop(store):
    """A model that always calls a tool and never answers must not hang the request — the
    recursion-limit catch in run_agent returns a bounded, honest message instead."""
    from backend.agents.planning import build_planning_agent
    from backend.agents.result import MAX_TOOL_CALLS, run_agent

    # Unique ids per turn — a real model never repeats a tool_call id, and langgraph's
    # bookkeeping assumes it won't either.
    always_call = [
        AIMessage(content="", tool_calls=[{"name": "get_hotspots", "args": {}, "id": f"call_{i}"}])
        for i in range(2 * MAX_TOOL_CALLS + 5)
    ]
    fake = FakeToolCallingModel(responses=always_call)
    graph = build_planning_agent(store, llm=fake)
    result = run_agent(graph, "keep going forever")

    assert "budget" in result.text.lower()


# --- Monitoring: deterministic trigger, no tool-calling loop -----------------------------------


@pytest.mark.parametrize(
    ("forecast_max_c", "expected"),
    [
        (36.9, None),
        (37.0, "advisory"),
        (44.9, "advisory"),
        (45.0, "heat_wave"),
        (46.9, "heat_wave"),
        (47.0, "severe_heat_wave"),
        (50.0, "severe_heat_wave"),
    ],
)
def test_severity_thresholds_match_the_imd_faq(forecast_max_c, expected):
    from backend.agents.monitoring import _severity

    assert _severity(forecast_max_c) == expected


def test_check_heatwave_no_trigger_never_calls_the_llm(store, monkeypatch):
    from backend import services
    from backend.agents.monitoring import check_heatwave
    from backend.schemas import WeatherDay, WeatherResponse

    monkeypatch.setattr(
        services,
        "get_weather",
        lambda days: WeatherResponse(
            days=[
                WeatherDay(
                    date="2026-07-27",
                    temp_max_c=32.0,
                    temp_min_c=25.0,
                    humidity_mean_pct=70.0,
                    wind_speed_max_ms=3.0,
                    precipitation_sum_mm=0.0,
                )
            ]
        ),
    )
    llm = MagicMock()
    assert check_heatwave(store, llm=llm) is None
    llm.invoke.assert_not_called()


def test_check_heatwave_triggered_drafts_with_the_llm_and_lists_wards(store, monkeypatch):
    from backend import services
    from backend.agents.monitoring import check_heatwave
    from backend.schemas import WeatherDay, WeatherResponse

    monkeypatch.setattr(
        services,
        "get_weather",
        lambda days: WeatherResponse(
            days=[
                WeatherDay(
                    date="2026-07-27",
                    temp_max_c=46.0,
                    temp_min_c=30.0,
                    humidity_mean_pct=60.0,
                    wind_speed_max_ms=3.0,
                    precipitation_sum_mm=0.0,
                )
            ]
        ),
    )
    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="Heat wave expected — take precautions.")

    alert = check_heatwave(store, llm=llm)

    assert alert is not None
    assert alert.severity == "heat_wave"
    assert alert.forecast_max_c == 46.0
    assert len(alert.wards_affected) == 5
    assert alert.summary == "Heat wave expected — take precautions."
    assert "not an official IMD warning" in alert.caveat
    llm.invoke.assert_called_once()
