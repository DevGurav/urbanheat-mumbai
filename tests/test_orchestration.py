"""The supervisor (routing + dispatch), `build_agent_layer`, and `POST /agent/chat` — tested
without a live LLM, same fake-model approach as `test_agents.py` (real tools, real store,
real graphs; only the model is scripted). Live routing/dispatch behavior against the real
Gemini API is a separate manual smoke test (devlog.md), not this suite.
"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from tests.test_agents import FakeToolCallingModel

# `store` and `retriever` are session-scoped fixtures from conftest.py.


# --- Supervisor.route: one classification call, parsed and validated in Python ----------------


@pytest.mark.parametrize(
    ("raw_response", "expected"),
    [
        ("copilot", "copilot"),
        ("Planning", "planning"),
        (" digital_twin \n", "digital_twin"),
        ("I'm not sure, maybe copilot?", "copilot"),  # unparseable -> falls back to copilot
        ("something_unrelated", "copilot"),
    ],
)
def test_route_parses_and_falls_back_safely(store, retriever, raw_response, expected):
    from backend.agents.supervisor import Supervisor

    fake = FakeToolCallingModel(responses=[AIMessage(content=raw_response)])
    supervisor = Supervisor(store, retriever, llm=fake)
    assert supervisor.route("some message") == expected


def test_handle_routes_then_dispatches_to_the_chosen_agent(store, retriever):
    from backend.agents.supervisor import Supervisor

    # Same fake model instance backs both the router call and the dispatched agent's own
    # loop — Supervisor shares one llm across the router and all three agents (by design,
    # ADR-0002's budget-aware construction), so responses are consumed in call order:
    # 1) the routing decision, 2) the planning agent's direct answer (no tool call scripted).
    fake = FakeToolCallingModel(
        responses=[
            AIMessage(content="planning"),
            AIMessage(content="Focus on ward L first."),
        ]
    )
    supervisor = Supervisor(store, retriever, llm=fake)
    result = supervisor.handle("what should we do about the hottest wards?")

    assert result.agent == "planning"
    assert result.text == "Focus on ward L first."
    assert result.tool_calls == []


def test_handle_surfaces_tool_calls_from_the_dispatched_agent(store, retriever):
    from backend.agents.supervisor import Supervisor

    fake = FakeToolCallingModel(
        responses=[
            AIMessage(content="digital_twin"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "simulate_scenario",
                        "args": {"ward_code": "A", "intervention": "greening", "coverage": 1.0},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="Cells like this one run cooler with greening."),
        ]
    )
    supervisor = Supervisor(store, retriever, llm=fake)
    result = supervisor.handle("what if we plant trees in ward A?")

    assert result.agent == "digital_twin"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "simulate_scenario"


# --- response cache: (question, data_version) -> ChatResult (agents.md §8, ADR-0011) ----------


def test_handle_is_cached_for_an_identical_question(store, retriever):
    from backend.agents.supervisor import Supervisor

    # Exactly one round trip's worth of scripted responses. If the second `handle()` call
    # were *not* served from cache, FakeToolCallingModel would raise IndexError trying to pop
    # a third response — the test fails loudly rather than silently passing on a real miss.
    fake = FakeToolCallingModel(
        responses=[
            AIMessage(content="copilot"),
            AIMessage(content="Ward B is hottest."),
        ]
    )
    supervisor = Supervisor(store, retriever, llm=fake)

    first = supervisor.handle("where is it hottest?")
    second = supervisor.handle("where is it hottest?")

    assert first == second
    assert first.text == "Ward B is hottest."


def test_handle_cache_is_exact_match_not_fuzzy(store, retriever):
    from backend.agents.supervisor import Supervisor

    fake = FakeToolCallingModel(
        responses=[
            AIMessage(content="copilot"),
            AIMessage(content="First answer."),
            AIMessage(content="planning"),
            AIMessage(content="Second answer."),
        ]
    )
    supervisor = Supervisor(store, retriever, llm=fake)

    first = supervisor.handle("where is it hottest?")
    # A differently-worded question is a genuine cache miss — runbook.md §5 warns about
    # exactly this: the cache does not fuzzy-match a rephrased question at demo time.
    second = supervisor.handle("where is it hottest right now?")

    assert first.text == "First answer."
    assert second.text == "Second answer."


def test_handle_cache_does_not_store_a_failed_call(store, retriever):
    from langchain_core.outputs import ChatGeneration
    from langchain_core.outputs import ChatResult as LCChatResult

    from backend.agents.supervisor import Supervisor

    class _FailsOnceThenRoutes(FakeToolCallingModel):
        """`bind_tools` must still return `self` (called at `create_agent` construction time,
        not lazily) — only `_generate`, the actual per-call path, fails then recovers.
        """

        _calls: int = 0

        def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> LCChatResult:
            self._calls += 1
            if self._calls == 1:
                raise RuntimeError("simulated upstream failure")
            return LCChatResult(generations=[ChatGeneration(message=AIMessage(content="planning"))])

    fake = _FailsOnceThenRoutes(responses=[])
    supervisor = Supervisor(store, retriever, llm=fake)

    with pytest.raises(RuntimeError, match="simulated upstream failure"):
        supervisor.handle("where is it hottest?")

    # The failed attempt must not have been cached — a second attempt gets a fresh compute(),
    # which here succeeds. If the failure had been cached, this would re-raise instead.
    assert supervisor.route("where is it hottest?") == "planning"


# --- build_agent_layer --------------------------------------------------------------------


def test_build_agent_layer_from_a_real_scenario_call(store):
    from backend import services
    from backend.agents.result import ToolCallRecord
    from backend.agents.supervisor import build_agent_layer

    scenario_result = services.scenario(store, "A", intervention="greening", coverage=1.0)
    call = ToolCallRecord(
        name="simulate_scenario",
        args={"ward_code": "A", "intervention": "greening"},
        result=scenario_result.model_dump_json(),
    )

    layer = build_agent_layer(store, [call])

    assert layer is not None
    assert layer["type"] == "FeatureCollection"
    assert len(layer["features"]) == scenario_result.n_cells
    assert "dlst" in layer["features"][0]["properties"]


def test_build_agent_layer_none_for_non_scenario_calls(store):
    from backend.agents.result import ToolCallRecord
    from backend.agents.supervisor import build_agent_layer

    call = ToolCallRecord(name="get_hotspots", args={}, result=json.dumps({"results": []}))
    assert build_agent_layer(store, [call]) is None


def test_build_agent_layer_none_when_the_scenario_call_errored(store):
    from backend.agents.result import ToolCallRecord
    from backend.agents.supervisor import build_agent_layer

    call = ToolCallRecord(
        name="simulate_scenario",
        args={"ward_code": "ZZ"},
        result=json.dumps({"error": "no ward", "error_code": "ward_not_found"}),
    )
    assert build_agent_layer(store, [call]) is None


def test_build_agent_layer_none_with_no_tool_calls(store):
    from backend.agents.supervisor import build_agent_layer

    assert build_agent_layer(store, []) is None


# --- POST /agent/chat, via the real app (real store, monkeypatched supervisor) ----------------


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    try:
        from backend.main import app

        with TestClient(app) as test_client:
            yield test_client
    except FileNotFoundError as exc:
        pytest.skip(f"artifacts not built: {exc}")
    except Exception as exc:  # noqa: BLE001 - a missing .env should skip, not error
        if ".env" in str(exc) or "config" in str(exc).lower():
            pytest.skip(str(exc))
        raise


def test_agent_chat_503s_when_supervisor_is_unavailable(client):
    # The real app's lifespan leaves app.state.supervisor as None whenever the RAG index or
    # GEMINI_API_KEY isn't available (main.py) — which is the honest state of this repo right
    # now (devlog.md, 2026-07-27). This test documents that as a 503, not a silent failure.
    if client.app.state.supervisor is not None:
        pytest.skip("a working supervisor is configured — the 503 path isn't reachable")
    resp = client.post("/agent/chat", json={"message": "where is it hottest?"})
    assert resp.status_code == 503
    assert resp.json()["error_code"] == "agent_layer_unavailable"


def test_agent_chat_reports_a_broken_llm_key_as_503_not_a_raw_500(client):
    """A *present but broken* GEMINI_API_KEY (runbook.md's 403 PERMISSION_DENIED entry) can't
    be caught at app startup — Supervisor construction alone doesn't make a call. It has to
    surface here, at request time, as a clean 503 rather than an unhandled traceback.
    """
    from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

    class _BrokenKeySupervisor:
        def handle(self, message: str):
            raise ChatGoogleGenerativeAIError("403 PERMISSION_DENIED: simulated broken key")

    client.app.state.supervisor = _BrokenKeySupervisor()
    resp = client.post("/agent/chat", json={"message": "where is it hottest?"})

    assert resp.status_code == 503
    assert resp.json()["error_code"] == "agent_upstream_unavailable"


def test_agent_chat_returns_the_full_contract_with_a_fake_supervisor(client):
    from backend.agents.result import ToolCallRecord
    from backend.agents.supervisor import ChatResult

    class _FakeSupervisor:
        def handle(self, message: str) -> ChatResult:
            return ChatResult(
                agent="copilot",
                text="Ward B is the hottest.",
                tool_calls=[
                    ToolCallRecord(name="get_hotspots", args={"n": 1}, result='{"results": []}')
                ],
            )

    client.app.state.supervisor = _FakeSupervisor()
    resp = client.post("/agent/chat", json={"message": "where is it hottest?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["agent"] == "copilot"
    assert body["text"] == "Ward B is the hottest."
    assert body["tool_calls"][0]["name"] == "get_hotspots"
    assert body["layer"] is None  # get_hotspots isn't mappable, unlike simulate_scenario


# --- backoff: explicit, not left at the library default (ADR-0002, backend/agents/llm.py) -----


def test_get_llm_sets_max_retries_explicitly(settings):
    if not settings.gemini_api_key:
        pytest.skip("GEMINI_API_KEY not set — get_llm() cannot construct a model")

    from backend.agents.llm import MAX_RETRIES, get_llm

    llm = get_llm()
    assert llm.max_retries == MAX_RETRIES
