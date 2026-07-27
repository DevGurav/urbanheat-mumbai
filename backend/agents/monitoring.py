"""Agent 4 — Monitoring: rule-based IMD thresholds in code, the LLM only drafts wording
(`agents.md` §7, canonical numbering ADR-0009). Not a tool-calling loop like the other three
agents — the trigger is deterministic, so there is nothing for an LLM to decide.

**Absolute-temperature thresholds only, not IMD's full criteria (ADR-0010).** IMD's official
Heat Wave rule for a coastal station like Mumbai needs both an absolute threshold and a
departure from the station's climatological normal maximum temperature. This project has no
real normal to depart from — only Phase 1's ERA5 dry-season *mean* air temperature
(`data_pipeline/sources/weather.py`), already found near-constant across the city and too
coarse to serve as a station normal. Using only the threshold path that needs no baseline
(IMD FAQ on Heat Wave, `data/knowledge_base/imd_faq_heatwave.txt`, option "b" — absolute
maximum temperature) keeps every number real and sourced, at the cost of firing less often
than the full criteria would. `agents.md` §7's own guardrail — alerts are advisory, never an
official IMD warning — already covers exactly this gap.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError

from backend import services
from backend.agents.llm import get_llm
from backend.store import Store

log = logging.getLogger("urbanheat.agents.monitoring")

SEVERE_HEAT_WAVE_C = 47.0  # IMD FAQ: Severe Heat Wave when actual max >= 47 C
HEAT_WAVE_C = 45.0  # IMD FAQ: Heat Wave when actual max >= 45 C
HEAT_ADVISORY_C = 37.0  # Mumbai's coastal base threshold, departure-from-normal not confirmed

CAVEAT = (
    "Based on forecast air temperature against IMD's absolute thresholds only — not IMD's "
    "full multi-station, departure-from-normal criteria (ADR-0010). Advisory, not an "
    "official IMD warning."
)


@dataclass(frozen=True)
class HeatwaveAlert:
    severity: str  # "advisory" | "heat_wave" | "severe_heat_wave"
    forecast_max_c: float
    wards_affected: list[str]
    summary: str
    caveat: str = field(default=CAVEAT)


def _severity(forecast_max_c: float) -> str | None:
    if forecast_max_c >= SEVERE_HEAT_WAVE_C:
        return "severe_heat_wave"
    if forecast_max_c >= HEAT_WAVE_C:
        return "heat_wave"
    if forecast_max_c >= HEAT_ADVISORY_C:
        return "advisory"
    return None


def _fallback_summary(severity: str, forecast_max_c: float, wards: list[str]) -> str:
    """A fixed-template summary, used when the LLM can't draft one. The *trigger* is
    deterministic and real regardless of whether an LLM is available to phrase it — Monitoring
    never lets a wording failure swallow a real alert (agents.md §7: the LLM only drafts
    wording, it never decides whether an alert exists).
    """
    return (
        f"A {severity.replace('_', ' ')} has been triggered: forecast maximum temperature "
        f"{forecast_max_c:.1f} C. Wards most exposed by Heat Vulnerability Index: "
        f"{', '.join(wards)}. Residents in these areas should take standard heat precautions "
        "(seek shade, stay hydrated, avoid midday exposure). This is a model-derived advisory, "
        "not an official IMD warning."
    )


def _draft_summary(
    severity: str, forecast_max_c: float, wards: list[str], llm: BaseChatModel | None
) -> str:
    prompt = (
        f"Draft a one-paragraph public advisory. A {severity.replace('_', ' ')} has been "
        f"deterministically triggered: forecast maximum temperature {forecast_max_c:.1f} C. "
        f"The wards most exposed by Heat Vulnerability Index are: {', '.join(wards)}. State "
        "the trigger fact plainly, name the wards, and tell residents to take standard heat "
        "precautions (shade, hydration, avoid midday exposure). Do not invent a cause, a "
        "duration, or any number not given above. This is a model-derived advisory, not an "
        "official IMD warning — say so."
    )
    try:
        model = llm or get_llm()
        response = model.invoke(prompt)
        # `.content` is not reliably a plain string (`backend/agents/result.py`'s same fix,
        # found live: Gemini can return a list of content blocks). `.text` normalizes it.
        return str(response.text)
    except (RuntimeError, ChatGoogleGenerativeAIError) as exc:
        # RuntimeError: get_llm() with no GEMINI_API_KEY set. ChatGoogleGenerativeAIError: a
        # real call failed (quota, a broken key — this exact project's own recent history).
        # Either way, the alert still exists; only its prose degrades.
        log.warning("monitoring: LLM wording draft unavailable (%s) — using the template", exc)
        return _fallback_summary(severity, forecast_max_c, wards)


def check_heatwave(store: Store, llm: BaseChatModel | None = None) -> HeatwaveAlert | None:
    """Deterministic trigger check + (only if triggered) one LLM call to draft the wording.
    Returns `None` on no trigger — most days, for Mumbai, that's the honest answer.
    """
    weather = services.get_weather(days=1)
    forecast_max_c = weather.days[0].temp_max_c
    severity = _severity(forecast_max_c)
    if severity is None:
        return None

    # "wards affected (forecast ∩ high HVI)" (agents.md §7) — one citywide forecast point, so
    # the intersection simplifies to: the top-HVI wards are the ones a citywide trigger hits
    # hardest.
    hotspots = services.hotspots(store, n=5, by="hvi", unit="ward")
    wards = [entry.ward_code for entry in hotspots.results]

    summary = _draft_summary(severity, forecast_max_c, wards, llm)
    return HeatwaveAlert(
        severity=severity, forecast_max_c=forecast_max_c, wards_affected=wards, summary=summary
    )
