"""The shared LLM binding for all four agents (ADR-0002 — Gemini Flash free tier).

Retry/backoff and the Groq fallback are the **Rate-limit hygiene** task group's job, not this
one's — `get_llm()` returns a plain, unwrapped chat model. Every agent module gets its model
through here, so there is exactly one place that reads `GEMINI_API_KEY`.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from data_pipeline.config import get_settings


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
    )
