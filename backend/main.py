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

from backend.routers import explain, grid, health, hotspots, weather
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
    yield


app = FastAPI(
    title="UrbanHeat AI API",
    version="0.3.0",
    summary="Surface urban heat, its drivers, and mitigation scenarios for Mumbai.",
    lifespan=lifespan,
)

# gzip first so large GeoJSON payloads are compressed (Render bandwidth — ADR-0003).
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(grid.router)
app.include_router(hotspots.router)
app.include_router(explain.router)
app.include_router(weather.router)


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
