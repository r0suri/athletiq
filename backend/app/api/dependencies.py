"""FastAPI dependency wiring. Tests can override any of these."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.repositories.checkins import CheckInRepository
from app.repositories.dynamodb import get_table
from app.repositories.profiles import ProfileRepository
from app.repositories.workouts import WorkoutRepository
from app.services.analytics import AnalyticsService
from app.services.checkins import CheckInService
from app.services.profiles import ProfileService
from app.services.workouts import WorkoutService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_workout_service(settings: SettingsDep) -> WorkoutService:
    return WorkoutService(WorkoutRepository(get_table(settings)))


def get_checkin_service(settings: SettingsDep) -> CheckInService:
    return CheckInService(CheckInRepository(get_table(settings)))


def get_profile_service(settings: SettingsDep) -> ProfileService:
    return ProfileService(ProfileRepository(get_table(settings)))


def get_analytics_service(settings: SettingsDep) -> AnalyticsService:
    table = get_table(settings)
    return AnalyticsService(
        WorkoutRepository(table), CheckInRepository(table), ProfileRepository(table)
    )


WorkoutServiceDep = Annotated[WorkoutService, Depends(get_workout_service)]
CheckInServiceDep = Annotated[CheckInService, Depends(get_checkin_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
