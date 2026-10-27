"""Response model for GET /v1/analytics/summary.

Mirrors the engine's dataclasses with explicit types so the OpenAPI schema (and a
generated TypeScript client) describes every field. Floats are rounded to 2 decimal
places (half-up) by the service before validation.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import Goal


class WeekVolumeOut(BaseModel):
    sessions: int
    training_days: int
    rest_days: int
    duration_min: float
    load: float = Field(description="Sum of session loads (duration_min x RPE), in AU")
    run_distance_km: float
    ride_distance_km: float
    sessions_missing_distance: int
    sessions_by_type: dict[str, int]
    strength_tonnage_kg: float


class LoadOut(BaseModel):
    load_7d: float
    load_previous_7d: float
    load_28d: float
    chronic_weekly_load: float | None
    weekly_change_pct: float | None
    acwr: float | None
    history_days: int


class ConsistencyOut(BaseModel):
    target_sessions_per_week: int
    weeks_evaluated: int
    weeks_meeting_target: int
    consistency_pct: float | None
    avg_sessions_per_week: float | None


class WellnessOut(BaseModel):
    sleep_nights_reported: int
    avg_sleep_hours: float | None
    fatigue_days_reported: int
    avg_fatigue: float | None
    soreness_days_reported: int
    avg_soreness: float | None
    days_with_fatigue_or_soreness: int
    high_fatigue_or_soreness_days: int


class FlagOut(BaseModel):
    code: str
    status: Literal["triggered", "not_triggered", "insufficient_data"]
    observed: float | None
    threshold: float
    explanation: str


class GoalSummaryOut(BaseModel):
    goal: Goal
    headline: str
    metrics: dict[str, float | None]


class DataQualityOut(BaseModel):
    workouts_received: int
    workouts_excluded: int
    exclusion_reasons: dict[str, int]
    checkin_values_ignored: int


class AnalyticsSummaryOut(BaseModel):
    as_of: date = Field(description="The user's local date the summary is calculated for")
    timezone: str
    profile_configured: bool
    goal: Goal
    current_week: WeekVolumeOut
    previous_week: WeekVolumeOut
    load: LoadOut
    consistency: ConsistencyOut
    wellness: WellnessOut
    flags: list[FlagOut]
    overall_status: Literal["insufficient_data", "no_flags", "caution", "elevated"]
    goal_summary: GoalSummaryOut
    data_quality: DataQualityOut
    disclaimer: str
