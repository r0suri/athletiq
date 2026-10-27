"""Workout endpoints. Thin: parse HTTP input, call the service, shape the response."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Query, Response, status

from app.api.dependencies import WorkoutServiceDep
from app.core.auth import CurrentUserDep
from app.domain.models import WorkoutType
from app.schemas.workouts import WorkoutCreate, WorkoutList, WorkoutOut

router = APIRouter(prefix="/workouts", tags=["workouts"])


@router.post("", response_model=WorkoutOut, status_code=status.HTTP_201_CREATED)
def create_workout(
    payload: Annotated[WorkoutCreate, Body()],
    user: CurrentUserDep,
    service: WorkoutServiceDep,
    response: Response,
) -> WorkoutOut:
    created = service.create(user.user_id, payload)
    response.headers["Location"] = f"/v1/workouts/{created.id}"
    return created


@router.get("", response_model=WorkoutList)
def list_workouts(
    user: CurrentUserDep,
    service: WorkoutServiceDep,
    from_: Annotated[date | None, Query(alias="from", description="Inclusive start date")] = None,
    to: Annotated[date | None, Query(description="Inclusive end date")] = None,
    type_: Annotated[Literal["run", "ride", "strength"] | None, Query(alias="type")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> WorkoutList:
    workout_type = WorkoutType(type_) if type_ else None
    return service.list(user.user_id, from_, to, limit, cursor, workout_type)


@router.get("/{workout_id}", response_model=WorkoutOut)
def get_workout(workout_id: str, user: CurrentUserDep, service: WorkoutServiceDep) -> WorkoutOut:
    return service.get(user.user_id, workout_id)


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: str, user: CurrentUserDep, service: WorkoutServiceDep) -> Response:
    service.delete(user.user_id, workout_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
