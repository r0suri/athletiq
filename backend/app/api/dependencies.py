"""FastAPI dependency wiring. Tests can override any of these."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories.checkins import CheckInRepository
from app.repositories.dynamodb import get_table
from app.repositories.workouts import WorkoutRepository
from app.services.checkins import CheckInService
from app.services.workouts import WorkoutService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_workout_service(settings: SettingsDep) -> WorkoutService:
    return WorkoutService(WorkoutRepository(get_table(settings)))


def get_checkin_service(settings: SettingsDep) -> CheckInService:
    return CheckInService(CheckInRepository(get_table(settings)))


WorkoutServiceDep = Annotated[WorkoutService, Depends(get_workout_service)]
CheckInServiceDep = Annotated[CheckInService, Depends(get_checkin_service)]
