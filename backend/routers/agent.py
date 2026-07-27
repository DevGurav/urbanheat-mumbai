"""POST /agent/chat — the natural-language interface over the three conversational agents
(`agents.md` §2, `api-reference.md`). Monitoring is not reachable here — it is cron-triggered,
not chat-triggered (`agents.md` §7).

The supervisor is built once at startup (`main.py`'s `lifespan`), not per request — it's
`None` if the RAG index or `GEMINI_API_KEY` isn't available at all, and this endpoint reports
that honestly as a 503. A *present but broken* key (runbook.md's `403 PERMISSION_DENIED`
entry) can't be caught at startup without spending a real call just to check — so that failure
surfaces here instead, as the same 503 rather than a raw traceback.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from backend.agents.supervisor import build_agent_layer
from backend.errors import api_error
from backend.schemas import AgentChatRequest, AgentChatResponse, AgentToolCall

router = APIRouter(tags=["agent"])


@router.post("/agent/chat", response_model=AgentChatResponse)
def agent_chat(request: Request, body: AgentChatRequest) -> AgentChatResponse:
    supervisor = request.app.state.supervisor
    if supervisor is None:
        raise api_error(
            503,
            "agent_layer_unavailable",
            "the agent layer isn't configured — the RAG index or GEMINI_API_KEY is missing "
            "(runbook.md)",
        )

    try:
        result = supervisor.handle(body.message)
    except ChatGoogleGenerativeAIError as exc:
        raise api_error(503, "agent_upstream_unavailable", str(exc)) from exc

    layer = build_agent_layer(request.app.state.store, result.tool_calls)
    return AgentChatResponse(
        agent=result.agent,
        text=result.text,
        tool_calls=[
            AgentToolCall(name=c.name, args=c.args, result=c.result) for c in result.tool_calls
        ],
        layer=layer,
    )
