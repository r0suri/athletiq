"""Loads a user's data with key-range queries and runs the deterministic engine.

The engine (app/domain/analytics.py) is unchanged; this service only decides
*which* records to pass and what "today" means for the user.
"""

from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.domain.analytics import compute_summary
from app.repositories.checkins import CheckInRepository
from app.repositories.profiles import ProfileRepository
from app.repositories.workouts import WorkoutRepository
from app.schemas.analytics import AnalyticsSummaryOut
from app.schemas.profile import DEFAULT_GOAL, DEFAULT_TIMEZONE

WORKOUT_WINDOW_DAYS = 28  # widest window the engine uses (28-day load, ACWR, consistency)
CHECKIN_WINDOW_DAYS = 7


def round_floats(value: Any, places: int = 2) -> Any:
    """Round every float to `places` decimals, half-up (Python's round() is half-even)."""
    if isinstance(value, float):
        quantum = Decimal(1).scaleb(-places)
        return float(Decimal(repr(value)).quantize(quantum, rounding=ROUND_HALF_UP))
    if isinstance(value, dict):
        return {k: round_floats(v, places) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [round_floats(v, places) for v in value]
    return value


def local_today(now_utc: datetime, timezone: str) -> date:
    return now_utc.astimezone(ZoneInfo(timezone)).date()


class AnalyticsService:
    def __init__(
        self,
        workouts: WorkoutRepository,
        checkins: CheckInRepository,
        profiles: ProfileRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._workouts = workouts
        self._checkins = checkins
        self._profiles = profiles
        self._clock = clock

    def summary(self, user_id: str) -> AnalyticsSummaryOut:
        profile = self._profiles.get(user_id)
        goal = profile.goal if profile else DEFAULT_GOAL
        timezone = profile.timezone if profile else DEFAULT_TIMEZONE
        as_of = local_today(self._clock(), timezone)

        window_start = as_of - timedelta(days=WORKOUT_WINDOW_DAYS - 1)
        records = [w.record for w in self._workouts.iter_range(user_id, window_start, as_of)]
        # The engine measures history from the first-ever workout (ACWR needs 28 days;
        # consistency skips weeks before history began). Passing that one older record
        # reproduces the full-history result without reading the full history: it lies
        # outside every summation window, so it changes no totals.
        earliest = self._workouts.earliest(user_id)
        if earliest is not None and earliest.record.workout_date < window_start:
            records.append(earliest.record)

        checkins = list(
            self._checkins.iter_range(
                user_id, as_of - timedelta(days=CHECKIN_WINDOW_DAYS - 1), as_of
            )
        )
        result = compute_summary(records, checkins, goal, as_of)

        payload = round_floats(asdict(result))
        payload["timezone"] = timezone
        payload["profile_configured"] = profile is not None
        return AnalyticsSummaryOut.model_validate(payload)
