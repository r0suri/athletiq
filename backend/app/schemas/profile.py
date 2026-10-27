"""User profile: training goal and IANA timezone."""

from datetime import datetime
from functools import lru_cache
from typing import Annotated
from zoneinfo import available_timezones

from pydantic import AfterValidator, BaseModel, ConfigDict

from app.domain.models import Goal

DEFAULT_GOAL = Goal.GENERAL_FITNESS
DEFAULT_TIMEZONE = "UTC"


@lru_cache
def _known_timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def check_timezone(value: str) -> str:
    # Whitelist against the IANA database rather than trying ZoneInfo(value), so odd
    # inputs (paths, empty strings) are rejected before reaching any file lookup.
    if value not in _known_timezones():
        raise ValueError("must be an IANA timezone name, e.g. 'America/New_York'")
    return value


Timezone = Annotated[str, AfterValidator(check_timezone)]


class ProfilePut(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    goal: Goal
    timezone: Timezone


class ProfileOut(BaseModel):
    goal: Goal
    timezone: str
    configured: bool  # False until the user saves a profile; values are defaults
    updated_at: datetime | None
