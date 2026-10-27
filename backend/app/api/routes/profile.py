"""The authenticated user's own profile."""

from typing import Annotated

from fastapi import APIRouter, Body

from app.api.dependencies import ProfileServiceDep
from app.core.auth import CurrentUserDep
from app.schemas.profile import ProfileOut, ProfilePut

router = APIRouter(prefix="/me", tags=["profile"])


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: CurrentUserDep, service: ProfileServiceDep) -> ProfileOut:
    return service.get(user.user_id)


@router.put("/profile", response_model=ProfileOut)
def put_profile(
    payload: Annotated[ProfilePut, Body()], user: CurrentUserDep, service: ProfileServiceDep
) -> ProfileOut:
    return service.put(user.user_id, payload)
