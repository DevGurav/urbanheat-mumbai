"""Pydantic response models — the typed contracts FastAPI renders into the OpenAPI schema.

Every response that carries model output includes `model_version` and `data_version`, and any
temperature field is labelled *surface* temperature (`measurement`) so a client cannot mistake
it for air temperature (ADR-0005, api-reference conventions).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

MEASUREMENT = "land_surface_temperature"


class Health(BaseModel):
    status: str = "ok"
    model_version: str
    data_version: str
    uptime_s: int
    n_cells: int = Field(description="Cells loaded in the in-memory store")
