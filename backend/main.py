"""FastAPI application — wiring, middleware, and the startup store.

uv run uvicorn backend.main:app --reload    # → http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from backend.routers import (
    agent,
    alerts,
    auth,
    explain,
    grid,
    health,
    hotspots,
    monitoring,
    predict,
    scenario,
    scenarios,
    trends,
    weather,
)
from backend.store import load_store
from data_pipeline.config import get_settings

settings = get_settings()
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("urbanheat.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("loading artifact store…")
    app.state.store = load_store()
    log.info(
        "store ready — model=%s data=%s, %d cells",
        app.state.store.model_version,
        app.state.store.data_version,
        len(app.state.store.features),
    )

    # The agent layer (Phase 4) is genuinely optional at startup: a fresh clone hasn't run
    # `backend.rag.ingest` yet, and a broken/missing GEMINI_API_KEY is a real, currently-open
    # issue (devlog.md 2026-07-27). Neither should stop the seven Phase 3 endpoints from
    # serving — /agent/chat degrades to a 503 instead (backend/routers/agent.py).
    # RuntimeError, not just FileNotFoundError: Retriever now embeds via Gemini's API
    # (ADR-0013), so a missing GEMINI_API_KEY fails construction the same way a missing
    # index does — both are "no RAG today," not a reason to refuse to boot.
    app.state.retriever = None
    app.state.supervisor = None
    try:
        from backend.rag.retrieve import Retriever

        app.state.retriever = Retriever()
    except (FileNotFoundError, RuntimeError) as exc:
        log.warning("RAG index unavailable, /agent/chat will 503: %s", exc)

    if app.state.retriever is not None:
        try:
            from backend.agents.supervisor import Supervisor

            app.state.supervisor = Supervisor(app.state.store, app.state.retriever)
            log.info("agent supervisor ready")
        except RuntimeError as exc:
            log.warning("agent supervisor unavailable, /agent/chat will 503: %s", exc)

    yield


app = FastAPI(
    title="UrbanHeat AI API",
    version="1.0.0",
    summary="Surface urban heat, its drivers, and mitigation scenarios for Mumbai.",
    lifespan=lifespan,
)

# gzip first so large GeoJSON payloads are compressed (Render bandwidth — ADR-0003).
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    # DELETE joined GET/POST for /scenarios/{id} (Phase 6's saved-scenarios endpoints).
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(grid.router)
app.include_router(hotspots.router)
app.include_router(explain.router)
app.include_router(weather.router)
app.include_router(predict.router)
app.include_router(scenario.router)
app.include_router(scenarios.router)
app.include_router(trends.router)
app.include_router(agent.router)
app.include_router(monitoring.router)
app.include_router(alerts.router)
app.include_router(auth.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Flatten `backend.errors.api_error`'s `{detail: {detail, error_code}}` to one level, so
    every error response is `{detail, error_code}` with a real HTTP status (api-reference.md).
    """
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail, "error_code": None}
    )


@app.get("/", include_in_schema=False)
def root(request: Request) -> dict:
    return {"service": "UrbanHeat AI API", "docs": "/docs", "health": "/health"}
