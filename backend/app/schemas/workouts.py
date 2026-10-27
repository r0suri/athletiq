"""HTTP request/response models for workouts.

Requests use a discriminated union on "type", so each workout type accepts only
its own fields (a run cannot carry exercises, a strength session has no distance).
extra="forbid" rejects unknown fields, including any attempt to send "user_id".
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.schemas.common import check_date_in_range

WorkoutDate = Annotated[date, AfterValidator(check_date_in_range)]
DurationMin = Annotated[float, Field(gt=0, le=1440, description="Minutes, 0 < x <= 1440")]
Rpe = Annotated[int, Field(ge=1, le=10, description="Session RPE, 1 (very easy) to 10 (max)")]
Notes = Annotated[str | None, Field(default=None, max_length=500)]


class _WorkoutBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    date: WorkoutDate
    duration_min: DurationMin
    rpe: Rpe
    notes: Notes = None


class RunCreate(_WorkoutBase):
    type: Literal["run"]
    distance_km: Annotated[float | None, Field(default=None, ge=0, le=500)] = None


class RideCreate(_WorkoutBase):
    type: Literal["ride"]
    distance_km: Annotated[float | None, Field(default=None, ge=0, le=1000)] = None


class ExerciseIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=80)]
    sets: Annotated[int, Field(ge=1, le=100)]
    reps: Annotated[int, Field(ge=1, le=1000)]
    weight_kg: Annotated[float, Field(ge=0, le=1000)] = 0.0


class StrengthCreate(_WorkoutBase):
    type: Literal["strength"]
    exercises: Annotated[list[ExerciseIn], Field(default_factory=list, max_length=50)]


WorkoutCreate = Annotated[RunCreate | RideCreate | StrengthCreate, Field(discriminator="type")]


class ExerciseOut(BaseModel):
    name: str
    sets: int
    reps: int
    weight_kg: float


class WorkoutOut(BaseModel):
    id: str
    type: Literal["run", "ride", "strength"]
    date: date
    duration_min: float
    rpe: int
    load: float = Field(description="Session load in arbitrary units: duration_min x rpe")
    distance_km: float | None = None
    exercises: list[ExerciseOut] = Field(default_factory=list)
    notes: str | None = None
    source: str
    created_at: datetime


class WorkoutList(BaseModel):
    items: list[WorkoutOut]
    next_cursor: str | None = Field(
        default=None, description="Pass as ?cursor= to fetch the next page; null when done."
    )
