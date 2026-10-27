"""Unit tests for the deterministic analytics engine (no AWS, no HTTP)."""

from datetime import date, timedelta

import pytest

from app.domain.analytics import (
    DISCLAIMER,
    compute_summary,
    percent_change,
    session_load,
    trailing_window,
)
from app.domain.models import DailyCheckIn, Goal, StrengthSet, WorkoutRecord, WorkoutType

AS_OF = date(2026, 10, 27)
RUN, RIDE, STRENGTH = WorkoutType.RUN, WorkoutType.RIDE, WorkoutType.STRENGTH


def d(month: int, day: int) -> date:
    return date(2026, month, day)


def w(day: date, kind: WorkoutType, minutes: float, rpe: int, km: float | None = None, **kw):
    return WorkoutRecord(day, kind, minutes, rpe, km, **kw)


def flag(summary, code: str):
    return next(f for f in summary.flags if f.code == code)


# ---------------------------------------------------------------------------
# Worked example (verify by hand: see docs/analytics.md)
# ---------------------------------------------------------------------------
def worked_example_workouts() -> list[WorkoutRecord]:
    baseline = []
    # Three baseline weeks, each: run 40min@5 (200 AU), strength 50min@6 (300), ride 60min@5 (300)
    for run_day, strength_day, ride_day in [
        (d(9, 30), d(10, 2), d(10, 4)),
        (d(10, 7), d(10, 9), d(10, 11)),
        (d(10, 14), d(10, 16), d(10, 18)),
    ]:
        baseline += [
            w(run_day, RUN, 40, 5, 7.0),
            w(strength_day, STRENGTH, 50, 6),
            w(ride_day, RIDE, 60, 5, 25.0),
        ]
    current = [
        w(d(10, 21), RUN, 45, 6, 8.0),  # 270 AU
        w(d(10, 22), STRENGTH, 60, 7),  # 420 AU
        w(d(10, 24), RIDE, 90, 6, 40.0),  # 540 AU
        w(d(10, 24), RUN, 30, 4, 5.0),  # 120 AU (second workout on the same day)
        w(d(10, 26), RUN, 50, 8, 10.0),  # 400 AU
    ]
    return baseline + current


def worked_example_checkins() -> list[DailyCheckIn]:
    return [
        DailyCheckIn(d(10, 24), fatigue=4),
        DailyCheckIn(d(10, 25), sleep_hours=5.0, fatigue=5, soreness=3),
        DailyCheckIn(d(10, 26), sleep_hours=5.5, fatigue=4),
    ]


def test_worked_example_matches_hand_calculation() -> None:
    s = compute_summary(worked_example_workouts(), worked_example_checkins(), Goal.ENDURANCE, AS_OF)

    cw = s.current_week
    assert cw.sessions == 5
    assert cw.training_days == 4  # Oct 21, 22, 24, 26
    assert cw.rest_days == 3
    assert cw.duration_min == 275  # 45 + 60 + 90 + 30 + 50
    assert cw.load == 1750  # 270 + 420 + 540 + 120 + 400
    assert cw.run_distance_km == pytest.approx(23.0)  # 8 + 5 + 10
    assert cw.ride_distance_km == pytest.approx(40.0)

    assert s.previous_week.load == 800  # Oct 14-20 baseline week
    assert s.load.load_28d == 4150  # 3 x 800 + 1750
    assert s.load.chronic_weekly_load == pytest.approx(800)  # 2400 / 3
    assert s.load.weekly_change_pct == pytest.approx(118.75)  # (1750 - 800) / 800 x 100
    assert s.load.acwr == pytest.approx(2.1875)  # 1750 / 800

    assert s.consistency.target_sessions_per_week == 4
    assert s.consistency.weeks_evaluated == 4
    assert s.consistency.weeks_meeting_target == 1  # only the current week has >= 4
    assert s.consistency.consistency_pct == pytest.approx(25.0)
    assert s.consistency.avg_sessions_per_week == pytest.approx(3.5)  # 14 / 4

    assert s.wellness.avg_fatigue == pytest.approx(13 / 3)  # (4 + 5 + 4) / 3
    assert s.wellness.soreness_days_reported == 1
    assert s.wellness.avg_soreness == pytest.approx(3.0)
    assert s.wellness.sleep_nights_reported == 2
    assert s.wellness.avg_sleep_hours == pytest.approx(5.25)

    assert flag(s, "weekly_load_jump").status == "triggered"
    assert flag(s, "acwr_spike").status == "triggered"
    assert flag(s, "sustained_fatigue").status == "triggered"
    assert flag(s, "short_sleep").status == "insufficient_data"  # only 2 nights reported
    assert s.overall_status == "elevated"

    assert s.goal_summary.metrics["endurance_distance_km"] == pytest.approx(63.0)
    assert s.goal_summary.metrics["previous_endurance_distance_km"] == pytest.approx(32.0)
    assert "+96.9%" in s.goal_summary.headline
    assert s.disclaimer == DISCLAIMER


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def test_session_load_is_duration_times_rpe() -> None:
    assert session_load(w(AS_OF, RUN, 45, 6)) == 270


def test_window_boundaries_are_inclusive() -> None:
    current = trailing_window(AS_OF, 7)
    previous = trailing_window(AS_OF, 7, offset_days=7)
    assert (current.start, current.end) == (d(10, 21), d(10, 27))
    assert (previous.start, previous.end) == (d(10, 14), d(10, 20))


def test_workout_seven_days_ago_belongs_to_previous_week() -> None:
    s = compute_summary([w(AS_OF - timedelta(days=7), RUN, 30, 5)], [], Goal.ENDURANCE, AS_OF)
    assert s.current_week.sessions == 0
    assert s.previous_week.sessions == 1


def test_percent_change_without_baseline_is_none() -> None:
    assert percent_change(500, 0) is None
    assert percent_change(150, 100) == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# Empty history
# ---------------------------------------------------------------------------
def test_empty_history_returns_zeros_and_no_false_flags() -> None:
    s = compute_summary([], [], Goal.GENERAL_FITNESS, AS_OF)

    assert s.current_week.sessions == 0
    assert s.current_week.rest_days == 7
    assert s.current_week.load == 0
    assert s.load.weekly_change_pct is None
    assert s.load.acwr is None
    assert s.load.history_days == 0
    assert s.consistency.consistency_pct is None
    assert s.wellness.avg_sleep_hours is None
    assert all(f.status == "insufficient_data" for f in s.flags)
    assert s.overall_status == "insufficient_data"
    assert s.data_quality.workouts_received == 0


# ---------------------------------------------------------------------------
# Missing values
# ---------------------------------------------------------------------------
def test_missing_distance_counts_session_but_not_distance() -> None:
    s = compute_summary(
        [w(AS_OF, RUN, 30, 5, None), w(AS_OF, RUN, 30, 5, 6.0)], [], Goal.ENDURANCE, AS_OF
    )
    assert s.current_week.sessions == 2
    assert s.current_week.run_distance_km == pytest.approx(6.0)
    assert s.current_week.sessions_missing_distance == 1


def test_missing_wellness_values_are_not_imputed() -> None:
    checkins = [
        DailyCheckIn(d(10, 25), sleep_hours=7.0),  # no fatigue or soreness
        DailyCheckIn(d(10, 26), fatigue=2),  # no sleep
        DailyCheckIn(d(10, 27)),  # nothing reported
    ]
    s = compute_summary([], checkins, Goal.GENERAL_FITNESS, AS_OF)
    assert s.wellness.sleep_nights_reported == 1
    assert s.wellness.avg_sleep_hours == pytest.approx(7.0)  # not averaged with zeros
    assert s.wellness.fatigue_days_reported == 1
    assert s.wellness.avg_soreness is None
    assert flag(s, "short_sleep").status == "insufficient_data"


def test_out_of_range_wellness_values_are_ignored_and_counted() -> None:
    checkins = [DailyCheckIn(AS_OF, sleep_hours=30.0, fatigue=9, soreness=0)]
    s = compute_summary([], checkins, Goal.GENERAL_FITNESS, AS_OF)
    assert s.wellness.avg_sleep_hours is None
    assert s.wellness.avg_fatigue is None
    assert s.data_quality.checkin_values_ignored == 3


def test_later_checkin_for_same_day_replaces_earlier() -> None:
    checkins = [DailyCheckIn(AS_OF, fatigue=5), DailyCheckIn(AS_OF, fatigue=2)]
    s = compute_summary([], checkins, Goal.GENERAL_FITNESS, AS_OF)
    assert s.wellness.avg_fatigue == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Zero-duration and invalid workouts
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("workout", "reason"),
    [
        (w(AS_OF, RUN, 0, 5), "non_positive_duration"),
        (w(AS_OF, RUN, -10, 5), "non_positive_duration"),
        (w(AS_OF, RUN, float("nan"), 5), "non_positive_duration"),
        (w(AS_OF, RUN, 2000, 5), "duration_exceeds_24h"),
        (w(AS_OF, RUN, 30, 0), "rpe_out_of_range"),
        (w(AS_OF, RUN, 30, 11), "rpe_out_of_range"),
        (w(AS_OF, RUN, 30, 5, -3.0), "invalid_distance"),
        (w(AS_OF + timedelta(days=1), RUN, 30, 5), "future_date"),
    ],
)
def test_invalid_workouts_are_excluded_with_reason(workout, reason) -> None:
    s = compute_summary([workout, w(AS_OF, RIDE, 60, 5, 20.0)], [], Goal.ENDURANCE, AS_OF)
    assert s.current_week.sessions == 1  # only the valid ride remains
    assert s.current_week.load == 300
    assert s.data_quality.workouts_received == 2
    assert s.data_quality.workouts_excluded == 1
    assert s.data_quality.exclusion_reasons == {reason: 1}


def test_zero_duration_workout_does_not_count_as_training_day() -> None:
    s = compute_summary([w(AS_OF, STRENGTH, 0, 5)], [], Goal.STRENGTH, AS_OF)
    assert s.current_week.training_days == 0
    assert s.current_week.rest_days == 7


# ---------------------------------------------------------------------------
# Multiple workouts on one day
# ---------------------------------------------------------------------------
def test_multiple_workouts_on_one_day_sum_load_but_count_one_training_day() -> None:
    same_day = [w(AS_OF, RUN, 30, 6, 5.0), w(AS_OF, STRENGTH, 45, 7), w(AS_OF, RIDE, 20, 3, 8.0)]
    s = compute_summary(same_day, [], Goal.GENERAL_FITNESS, AS_OF)
    assert s.current_week.sessions == 3
    assert s.current_week.training_days == 1
    assert s.current_week.rest_days == 6
    assert s.current_week.load == 30 * 6 + 45 * 7 + 20 * 3  # 555


# ---------------------------------------------------------------------------
# Large changes in training volume
# ---------------------------------------------------------------------------
def _two_weeks(previous_load_minutes: float, current_load_minutes: float) -> list[WorkoutRecord]:
    # RPE 5 so load = 5 x minutes
    return [
        w(AS_OF - timedelta(days=8), RUN, previous_load_minutes, 5, 5.0),
        w(AS_OF - timedelta(days=1), RUN, current_load_minutes, 5, 5.0),
    ]


def test_large_increase_triggers_weekly_jump() -> None:
    s = compute_summary(_two_weeks(60, 120), [], Goal.ENDURANCE, AS_OF)  # 300 -> 600 AU
    f = flag(s, "weekly_load_jump")
    assert f.status == "triggered"
    assert f.observed == pytest.approx(100.0)


def test_increase_at_threshold_does_not_trigger() -> None:
    s = compute_summary(_two_weeks(100, 130), [], Goal.ENDURANCE, AS_OF)  # exactly +30%
    assert flag(s, "weekly_load_jump").status == "not_triggered"


def test_large_decrease_is_not_flagged() -> None:
    s = compute_summary(_two_weeks(120, 30), [], Goal.ENDURANCE, AS_OF)  # -75%
    f = flag(s, "weekly_load_jump")
    assert f.status == "not_triggered"
    assert f.observed == pytest.approx(-75.0)


def test_small_baseline_is_not_compared() -> None:
    s = compute_summary(_two_weeks(10, 100), [], Goal.ENDURANCE, AS_OF)  # 50 AU baseline
    assert flag(s, "weekly_load_jump").status == "insufficient_data"


def test_acwr_needs_28_days_of_history() -> None:
    workouts = [w(AS_OF - timedelta(days=26), RUN, 60, 5), w(AS_OF, RUN, 60, 5)]
    s = compute_summary(workouts, [], Goal.ENDURANCE, AS_OF)
    assert s.load.history_days == 27
    assert s.load.acwr is None
    assert flag(s, "acwr_spike").status == "insufficient_data"


def test_steady_training_has_acwr_near_one() -> None:
    # One identical session in each 7-day block; the first is exactly 27 days before as_of.
    workouts = [w(AS_OF - timedelta(days=6 + 7 * i), RUN, 60, 5, 10.0) for i in range(4)]
    s = compute_summary(workouts, [], Goal.ENDURANCE, AS_OF)
    assert s.load.history_days == 28
    assert s.load.acwr == pytest.approx(1.0)
    assert flag(s, "acwr_spike").status == "not_triggered"
    assert s.overall_status == "no_flags"


# ---------------------------------------------------------------------------
# Different workout categories and goals
# ---------------------------------------------------------------------------
def mixed_week() -> list[WorkoutRecord]:
    squat = StrengthSet("back squat", sets=5, reps=5, weight_kg=100)
    pushup = StrengthSet("push-up", sets=3, reps=15)  # bodyweight -> 0 kg
    return [
        w(d(10, 22), RUN, 40, 6, 8.0),
        w(d(10, 23), RIDE, 75, 5, 30.0),
        w(d(10, 25), STRENGTH, 50, 7, exercises=(squat, pushup)),
        w(d(10, 27), STRENGTH, 40, 6, exercises=(squat,)),
    ]


def test_categories_are_counted_and_distances_kept_separate() -> None:
    s = compute_summary(mixed_week(), [], Goal.GENERAL_FITNESS, AS_OF)
    cw = s.current_week
    assert cw.sessions_by_type == {"run": 1, "ride": 1, "strength": 2}
    assert cw.run_distance_km == pytest.approx(8.0)
    assert cw.ride_distance_km == pytest.approx(30.0)
    assert cw.sessions_missing_distance == 0  # strength never needs distance
    assert cw.strength_tonnage_kg == pytest.approx(5000)  # 2 x (5 x 5 x 100)


def test_strength_goal_summary() -> None:
    s = compute_summary(mixed_week(), [], Goal.STRENGTH, AS_OF)
    assert s.goal_summary.metrics["strength_sessions"] == 2
    assert s.goal_summary.metrics["target_sessions"] == 3
    assert "2 of 3 target strength sessions" in s.goal_summary.headline
    assert "5,000 kg" in s.goal_summary.headline


def test_general_fitness_goal_summary() -> None:
    s = compute_summary(mixed_week(), [], Goal.GENERAL_FITNESS, AS_OF)
    assert s.goal_summary.metrics["active_minutes"] == 205
    assert s.goal_summary.metrics["activity_types"] == 3
    assert "205 active minutes" in s.goal_summary.headline


def test_endurance_goal_summary_without_previous_week() -> None:
    s = compute_summary(mixed_week(), [], Goal.ENDURANCE, AS_OF)
    assert s.goal_summary.metrics["endurance_distance_km"] == pytest.approx(38.0)
    assert "no previous-week data" in s.goal_summary.headline


# ---------------------------------------------------------------------------
# Wellness flags
# ---------------------------------------------------------------------------
def test_short_sleep_triggers_with_three_nights() -> None:
    checkins = [DailyCheckIn(AS_OF - timedelta(days=i), sleep_hours=5.5) for i in range(3)]
    f = flag(compute_summary([], checkins, Goal.GENERAL_FITNESS, AS_OF), "short_sleep")
    assert f.status == "triggered"
    assert f.observed == pytest.approx(5.5)


def test_fatigue_on_two_of_five_days_is_not_sustained() -> None:
    scores = [5, 4, 2, 1, 2]
    checkins = [DailyCheckIn(AS_OF - timedelta(days=i), fatigue=v) for i, v in enumerate(scores)]
    f = flag(compute_summary([], checkins, Goal.GENERAL_FITNESS, AS_OF), "sustained_fatigue")
    assert f.status == "not_triggered"
    assert f.observed == 2


def test_engine_is_deterministic() -> None:
    args = (worked_example_workouts(), worked_example_checkins(), Goal.ENDURANCE, AS_OF)
    assert compute_summary(*args) == compute_summary(*args)
