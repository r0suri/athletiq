"""Deterministic training-analytics engine.

Pure functions only: no I/O, no clock reads. Every calculation is relative to an
explicit `as_of` date so results are reproducible and unit-testable.
See docs/analytics.md for the formulas and their trade-offs.
"""

import math
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from app.domain.goals import GOAL_TARGET_SESSIONS, GoalSummary, build_goal_summary
from app.domain.heuristics import Flag, evaluate_flags, overall_status
from app.domain.models import DailyCheckIn, Goal, WorkoutRecord, WorkoutType

RPE_MIN, RPE_MAX = 1, 10
MAX_DURATION_MIN = 24 * 60
WELLNESS_SCALE_MIN, WELLNESS_SCALE_MAX = 1, 5
ACWR_MIN_HISTORY_DAYS = 28

DISCLAIMER = (
    "These training-load indicators are heuristic estimates calculated from your logged "
    "sessions and self-reported wellness. They are not medical measurements, are not "
    "medically validated, and do not predict injury."
)


# ---------------------------------------------------------------------------
# Date windows
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DateWindow:
    start: date
    end: date  # inclusive

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end


def trailing_window(as_of: date, days: int, offset_days: int = 0) -> DateWindow:
    """The `days`-long window ending `offset_days` before `as_of` (inclusive)."""
    end = as_of - timedelta(days=offset_days)
    return DateWindow(start=end - timedelta(days=days - 1), end=end)


# ---------------------------------------------------------------------------
# Validation and session load
# ---------------------------------------------------------------------------
def session_load(workout: WorkoutRecord) -> float:
    """Foster session-RPE load in arbitrary units (AU): duration x RPE."""
    return workout.duration_min * workout.rpe


def validation_issues(workout: WorkoutRecord, as_of: date) -> list[str]:
    issues: list[str] = []
    duration = workout.duration_min
    if not isinstance(duration, int | float) or not math.isfinite(duration) or duration <= 0:
        issues.append("non_positive_duration")
    elif duration > MAX_DURATION_MIN:
        issues.append("duration_exceeds_24h")
    rpe = workout.rpe
    if isinstance(rpe, bool) or not isinstance(rpe, int) or not RPE_MIN <= rpe <= RPE_MAX:
        issues.append("rpe_out_of_range")
    distance = workout.distance_km
    if distance is not None and (not math.isfinite(distance) or distance < 0):
        issues.append("invalid_distance")
    if workout.workout_date > as_of:
        issues.append("future_date")
    return issues


@dataclass(frozen=True)
class DataQuality:
    workouts_received: int
    workouts_excluded: int
    exclusion_reasons: dict[str, int]
    checkin_values_ignored: int


def partition_workouts(
    workouts: Iterable[WorkoutRecord], as_of: date
) -> tuple[list[WorkoutRecord], Counter[str], int]:
    valid: list[WorkoutRecord] = []
    reasons: Counter[str] = Counter()
    received = 0
    for workout in workouts:
        received += 1
        issues = validation_issues(workout, as_of)
        if issues:
            reasons.update(issues)
        else:
            valid.append(workout)
    return valid, reasons, received


# ---------------------------------------------------------------------------
# Volume, frequency, rest days
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WeekVolume:
    sessions: int
    training_days: int
    rest_days: int
    duration_min: float
    load: float
    run_distance_km: float
    ride_distance_km: float
    sessions_missing_distance: int
    sessions_by_type: dict[str, int]
    strength_tonnage_kg: float


def _in_window(workouts: Iterable[WorkoutRecord], window: DateWindow) -> list[WorkoutRecord]:
    return [w for w in workouts if window.contains(w.workout_date)]


def compute_week_volume(valid: Sequence[WorkoutRecord], window: DateWindow) -> WeekVolume:
    week = _in_window(valid, window)
    training_days = len({w.workout_date for w in week})
    by_type = {t.value: 0 for t in WorkoutType}
    run_km = ride_km = 0.0
    missing_distance = 0
    tonnage = 0.0
    for w in week:
        by_type[w.workout_type.value] += 1
        if w.workout_type in (WorkoutType.RUN, WorkoutType.RIDE):
            if w.distance_km is None:
                missing_distance += 1
            elif w.workout_type is WorkoutType.RUN:
                run_km += w.distance_km
            else:
                ride_km += w.distance_km
        if w.workout_type is WorkoutType.STRENGTH:
            tonnage += sum(s.sets * s.reps * s.weight_kg for s in w.exercises)
    window_days = (window.end - window.start).days + 1
    return WeekVolume(
        sessions=len(week),
        training_days=training_days,
        rest_days=window_days - training_days,
        duration_min=sum(w.duration_min for w in week),
        load=sum(session_load(w) for w in week),
        run_distance_km=run_km,
        ride_distance_km=ride_km,
        sessions_missing_distance=missing_distance,
        sessions_by_type=by_type,
        strength_tonnage_kg=tonnage,
    )


# ---------------------------------------------------------------------------
# Training load
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LoadMetrics:
    load_7d: float
    load_previous_7d: float
    load_28d: float
    chronic_weekly_load: float | None  # mean weekly load of the 21 days before this week
    weekly_change_pct: float | None
    acwr: float | None
    history_days: int


def percent_change(current: float, previous: float) -> float | None:
    """Relative change in percent; None when there is no previous baseline."""
    if previous <= 0:
        return None
    return (current - previous) / previous * 100


def compute_load_metrics(valid: Sequence[WorkoutRecord], as_of: date) -> LoadMetrics:
    def load_in(window: DateWindow) -> float:
        return sum(session_load(w) for w in _in_window(valid, window))

    load_7d = load_in(trailing_window(as_of, 7))
    load_prev = load_in(trailing_window(as_of, 7, offset_days=7))
    load_28d = load_in(trailing_window(as_of, 28))
    chronic_total = load_in(trailing_window(as_of, 21, offset_days=7))

    history_days = (as_of - min(w.workout_date for w in valid)).days + 1 if valid else 0
    has_history = history_days >= ACWR_MIN_HISTORY_DAYS
    chronic = chronic_total / 3 if has_history else None
    acwr = load_7d / chronic if chronic else None  # None when chronic is None or 0

    return LoadMetrics(
        load_7d=load_7d,
        load_previous_7d=load_prev,
        load_28d=load_28d,
        chronic_weekly_load=chronic,
        weekly_change_pct=percent_change(load_7d, load_prev),
        acwr=acwr,
        history_days=history_days,
    )


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Consistency:
    target_sessions_per_week: int
    weeks_evaluated: int
    weeks_meeting_target: int
    consistency_pct: float | None
    avg_sessions_per_week: float | None


def compute_consistency(valid: Sequence[WorkoutRecord], as_of: date, goal: Goal) -> Consistency:
    target = GOAL_TARGET_SESSIONS[goal]
    if not valid:
        return Consistency(target, 0, 0, None, None)
    first_day = min(w.workout_date for w in valid)
    blocks = [trailing_window(as_of, 7, offset_days=7 * i) for i in range(4)]
    evaluated = [b for b in blocks if b.end >= first_day]  # skip blocks before history began
    counts = [len(_in_window(valid, b)) for b in evaluated]
    meeting = sum(1 for c in counts if c >= target)
    return Consistency(
        target_sessions_per_week=target,
        weeks_evaluated=len(evaluated),
        weeks_meeting_target=meeting,
        consistency_pct=meeting / len(evaluated) * 100,
        avg_sessions_per_week=sum(counts) / len(evaluated),
    )


# ---------------------------------------------------------------------------
# Wellness (optional, never imputed)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Wellness:
    sleep_nights_reported: int
    avg_sleep_hours: float | None
    fatigue_days_reported: int
    avg_fatigue: float | None
    soreness_days_reported: int
    avg_soreness: float | None
    days_with_fatigue_or_soreness: int  # days with at least one of the two reported
    high_fatigue_or_soreness_days: int  # days where fatigue >= 4 or soreness >= 4


def _clean_scale(value: int | None) -> tuple[int | None, bool]:
    """Return (value or None, was_invalid)."""
    if value is None:
        return None, False
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not WELLNESS_SCALE_MIN <= value <= WELLNESS_SCALE_MAX
    ):
        return None, True
    return value, False


def _clean_sleep(value: float | None) -> tuple[float | None, bool]:
    if value is None:
        return None, False
    if not isinstance(value, int | float) or not math.isfinite(value) or not 0 <= value <= 24:
        return None, True
    return float(value), False


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def compute_wellness(checkins: Iterable[DailyCheckIn], window: DateWindow) -> tuple[Wellness, int]:
    """Returns the wellness summary and the number of invalid values ignored."""
    latest: dict[date, DailyCheckIn] = {}
    for c in checkins:  # one check-in per day; a later entry for the same day wins
        if window.contains(c.checkin_date):
            latest[c.checkin_date] = c

    sleep: list[float] = []
    fatigue: list[float] = []
    soreness: list[float] = []
    ignored = 0
    days_reported = 0
    high_days = 0
    for c in latest.values():
        s, bad_s = _clean_sleep(c.sleep_hours)
        f, bad_f = _clean_scale(c.fatigue)
        r, bad_r = _clean_scale(c.soreness)
        ignored += bad_s + bad_f + bad_r
        if s is not None:
            sleep.append(s)
        if f is not None:
            fatigue.append(f)
        if r is not None:
            soreness.append(r)
        if f is not None or r is not None:
            days_reported += 1
            if (f or 0) >= 4 or (r or 0) >= 4:
                high_days += 1

    wellness = Wellness(
        sleep_nights_reported=len(sleep),
        avg_sleep_hours=_mean(sleep),
        fatigue_days_reported=len(fatigue),
        avg_fatigue=_mean(fatigue),
        soreness_days_reported=len(soreness),
        avg_soreness=_mean(soreness),
        days_with_fatigue_or_soreness=days_reported,
        high_fatigue_or_soreness_days=high_days,
    )
    return wellness, ignored


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AnalyticsSummary:
    as_of: date
    goal: Goal
    current_week: WeekVolume
    previous_week: WeekVolume
    load: LoadMetrics
    consistency: Consistency
    wellness: Wellness
    flags: list[Flag]
    overall_status: str
    goal_summary: GoalSummary
    data_quality: DataQuality
    disclaimer: str = DISCLAIMER


def compute_summary(
    workouts: Iterable[WorkoutRecord],
    checkins: Iterable[DailyCheckIn],
    goal: Goal,
    as_of: date,
) -> AnalyticsSummary:
    valid, reasons, received = partition_workouts(workouts, as_of)
    current = compute_week_volume(valid, trailing_window(as_of, 7))
    previous = compute_week_volume(valid, trailing_window(as_of, 7, offset_days=7))
    load = compute_load_metrics(valid, as_of)
    wellness, ignored = compute_wellness(checkins, trailing_window(as_of, 7))
    flags = evaluate_flags(load, wellness)

    return AnalyticsSummary(
        as_of=as_of,
        goal=goal,
        current_week=current,
        previous_week=previous,
        load=load,
        consistency=compute_consistency(valid, as_of, goal),
        wellness=wellness,
        flags=flags,
        overall_status=overall_status(flags),
        goal_summary=build_goal_summary(goal, current, previous),
        data_quality=DataQuality(
            workouts_received=received,
            workouts_excluded=received - len(valid),
            exclusion_reasons=dict(sorted(reasons.items())),
            checkin_values_ignored=ignored,
        ),
    )
