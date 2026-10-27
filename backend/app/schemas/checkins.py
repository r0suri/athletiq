"""HTTP models for daily wellness check-ins. All fields are optional, but a check-in
must report at least one value. PUT replaces the whole check-in for that date."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CheckInPut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sleep_hours: Annotated[float | None, Field(default=None, ge=0, le=24)] = None
    fatigue: Annotated[
        int | None, Field(default=None, ge=1, le=5, description="1 fresh, 5 exhausted")
    ] = None
    soreness: Annotated[
        int | None, Field(default=None, ge=1, le=5, description="1 none, 5 very sore")
    ] = None

    @model_validator(mode="after")
    def _at_least_one_value(self) -> "CheckInPut":
        if self.sleep_hours is None and self.fatigue is None and self.soreness is None:
            raise ValueError("provide at least one of sleep_hours, fatigue or soreness")
        return self


class CheckInOut(BaseModel):
    date: date
    sleep_hours: float | None
    fatigue: int | None
    soreness: int | None
    updated_at: datetime
