"""POST/GET/DELETE /scenarios — saved scenario configs (Phase 6, `supabase/schema.sql`).

Stores the scenario CONFIG only, never a computed result: loading a saved scenario means the
frontend re-calls the real `POST /scenario` with these fields, so what a user sees is always
freshly computed against the current model, never a stale snapshot that silently drifted from
a retrained one (PROGRESS.md's kickoff decision, restated in `schema.sql`'s own comment).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend import saved_scenarios
from backend.auth import AuthUser, get_current_user
from backend.errors import api_error
from backend.schemas import SavedScenario, SavedScenarioRequest, SavedScenariosResponse

router = APIRouter(tags=["scenarios"])


@router.get("/scenarios", response_model=SavedScenariosResponse)
def list_scenarios(user: AuthUser = Depends(get_current_user)) -> SavedScenariosResponse:
    rows = saved_scenarios.list_saved_scenarios(user.access_token)
    return SavedScenariosResponse(scenarios=[SavedScenario(**row) for row in rows])


@router.post("/scenarios", response_model=SavedScenario, status_code=201)
def save_scenario(
    req: SavedScenarioRequest, user: AuthUser = Depends(get_current_user)
) -> SavedScenario:
    row = saved_scenarios.create_saved_scenario(user.access_token, user.id, req)
    return SavedScenario(**row)


@router.delete("/scenarios/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: str, user: AuthUser = Depends(get_current_user)) -> None:
    deleted = saved_scenarios.delete_saved_scenario(user.access_token, scenario_id)
    if not deleted:
        raise api_error(404, "scenario_not_found", "No saved scenario with that id")
