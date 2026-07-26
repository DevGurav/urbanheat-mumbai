"""Liveness + versions — also the endpoint used to wake Render before a demo (api-reference)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.schemas import Health

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=Health)
def health(request: Request) -> Health:
    store = request.app.state.store
    return Health(
        status="ok",
        model_version=store.model_version,
        data_version=store.data_version,
        uptime_s=store.uptime_s,
        n_cells=len(store.features),
    )
