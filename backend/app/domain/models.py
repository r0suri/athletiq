"""Framework-free domain types used by the analytics engine.

These are plain frozen dataclasses: no FastAPI, Pydantic, or boto3. The API layer
validates input and maps it into these types; the repository layer maps stored
items into them. That keeps the analytics engine pure and trivially testable.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class WorkoutType(StrEnum):
    RUN = "run"
    RIDE = "ride"
    STRENGTH = "strength"


class Goal(StrEnum):
    STRENGTH = "strength"
    ENDURANCE = "endurance"
    GENERAL_FITNESS = "general_fitness"


@dataclass(frozen=True)
class StrengthSet:
    exercise: str
    sets: int
    reps: int
    weight_kg: float = 0.0  # 0 for bodyweight movements


@dataclass(frozen=True)
class WorkoutRecord:
    workout_date: date  # the user's local calendar date
    workout_type: WorkoutType
    duration_min: float
    rpe: int  # session RPE, 1 (very easy) to 10 (maximal)
    distance_km: float | None = None  # runs and rides only; None means "not recorded"
    exercises: tuple[StrengthSet, ...] = ()


@dataclass(frozen=True)
class DailyCheckIn:
    """Optional self-reported wellness for one day. Every field may be missing."""

    checkin_date: date
    sleep_hours: float | None = None  # 0 to 24
    fatigue: int | None = None  # 1 (fresh) to 5 (exhausted)
    soreness: int | None = None  # 1 (none) to 5 (very sore)
