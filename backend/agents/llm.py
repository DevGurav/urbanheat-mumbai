"""The shared LLM binding for all four agents (ADR-0002 — Gemini Flash free tier).

The Groq fallback in `agents.md` §8's original rate-limit plan was dropped for the Phase 4
MVP (ADR-0011) — `get_llm()` only ever returns a Gemini-backed model. Every agent module gets
its model through here, so there is exactly one place that reads `GEMINI_API_KEY`.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from data_pipeline.config import get_settings

# Backoff on 429 (agents.md §8, ADR-0002). `ChatGoogleGenerativeAI` retries with exponential
# backoff internally (langchain-google-genai wraps `google-genai`'s own tenacity retry) —
# live-verified during the Phase 4 agents build (devlog.md, 2026-07-27): observed 1s/2s/4s/8s
# delays before finally raising. The library default is 6 retries, which on a real quota
# error can mean 30+ seconds before `/agent/chat` responds — too long for an interactive
# request that api-reference.md already documents as "the client shows a thinking state," not
# "the client waits half a minute." Set explicitly, not left at the library default, so the
# bound is a documented choice: enough to ride out a genuine transient blip, not so much that
# a doomed request (daily quota actually exhausted) makes the caller wait needlessly.
MAX_RETRIES = 3


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set — every agent needs a working LLM (ADR-0002); "
            "see .env.example and runbook.md §1.2"
        )
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.gemini_api_key,
        temperature=temperature,
        max_retries=MAX_RETRIES,
    )
