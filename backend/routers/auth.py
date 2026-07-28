"""GET /auth/me — confirms a bearer token is a live Supabase session and echoes who it
belongs to. Used by the frontend right after the magic-link redirect to verify the session
actually took, and as the one endpoint that exercises `backend.auth.get_current_user`
end-to-end until the saved-scenarios endpoints (Phase 6's next task group) give it a real
write path to guard.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.auth import AuthUser, get_current_user
from backend.schemas import AuthUserResponse

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=AuthUserResponse)
def me(user: AuthUser = Depends(get_current_user)) -> AuthUserResponse:
    return AuthUserResponse(id=user.id, email=user.email)
