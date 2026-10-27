"""Transparent, rule-based training-load and wellness flags.

Each rule has a fixed threshold and returns the observed value, the threshold and
a plain-English explanation, so a user (or reviewer) can verify every result.
These are heuristics for awareness, NOT a medically validated injury predictor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.domain.analytics import LoadMetrics, Wellness

FlagStatus = Literal["triggered", "not_triggered", "insufficient_data"]

WEEKLY_JUMP_PCT = 30.0
WEEKLY_JUMP_MIN_BASELINE_AU = 150.0
ACWR_HIGH = 1.5
HIGH_WELLNESS_SCORE = 4
SUSTAINED_FATIGUE_MIN_DAYS = 3
SHORT_SLEEP_HOURS = 6.0
MIN_REPORTED_DAYS = 3


@dataclass(frozen=True)
class Flag:
    code: str
    status: FlagStatus
    observed: float | None
    threshold: float
    explanation: str


def weekly_load_jump(load: LoadMetrics) -> Flag:
    code, threshold = "weekly_load_jump", WEEKLY_JUMP_PCT
    if load.load_previous_7d < WEEKLY_JUMP_MIN_BASELINE_AU or load.weekly_change_pct is None:
        return Flag(
            code,
            "insufficient_data",
            None,
            threshold,
            f"Needs at least {WEEKLY_JUMP_MIN_BASELINE_AU:.0f} AU of load in the previous "
            f"7 days to compare against (found {load.load_previous_7d:.0f} AU).",
        )
    change = load.weekly_change_pct
    if change > threshold:
        return Flag(
            code,
            "triggered",
            change,
            threshold,
            f"7-day load rose {change:.1f}% versus the previous 7 days "
            f"({load.load_previous_7d:.0f} to {load.load_7d:.0f} AU), above the "
            f"{threshold:.0f}% heuristic threshold.",
        )
    return Flag(
        code,
        "not_triggered",
        change,
        threshold,
        f"7-day load changed {change:+.1f}% versus the previous 7 days, within the "
        f"{threshold:.0f}% heuristic threshold.",
    )


def acwr_spike(load: LoadMetrics) -> Flag:
    code, threshold = "acwr_spike", ACWR_HIGH
    if load.acwr is None:
        return Flag(
            code,
            "insufficient_data",
            None,
            threshold,
            "Needs 28 days of training history and some load in the 3 weeks before this week.",
        )
    status: FlagStatus = "triggered" if load.acwr > threshold else "not_triggered"
    relation = "above" if status == "triggered" else "at or below"
    return Flag(
        code,
        status,
        load.acwr,
        threshold,
        f"This week's load is {load.acwr:.2f}x your average weekly load over the previous "
        f"3 weeks, {relation} the {threshold} heuristic threshold.",
    )


def sustained_fatigue(wellness: Wellness) -> Flag:
    code, threshold = "sustained_fatigue", float(SUSTAINED_FATIGUE_MIN_DAYS)
    days = wellness.days_with_fatigue_or_soreness
    if days < MIN_REPORTED_DAYS:
        return Flag(
            code,
            "insufficient_data",
            None,
            threshold,
            f"Needs fatigue or soreness check-ins on at least {MIN_REPORTED_DAYS} of the last "
            f"7 days (found {days}).",
        )
    high = wellness.high_fatigue_or_soreness_days
    status: FlagStatus = "triggered" if high >= SUSTAINED_FATIGUE_MIN_DAYS else "not_triggered"
    return Flag(
        code,
        status,
        float(high),
        threshold,
        f"Fatigue or soreness was rated {HIGH_WELLNESS_SCORE}+ out of 5 on {high} of "
        f"{days} reported days (flag at {SUSTAINED_FATIGUE_MIN_DAYS}+ days).",
    )


def short_sleep(wellness: Wellness) -> Flag:
    code, threshold = "short_sleep", SHORT_SLEEP_HOURS
    nights = wellness.sleep_nights_reported
    if nights < MIN_REPORTED_DAYS or wellness.avg_sleep_hours is None:
        return Flag(
            code,
            "insufficient_data",
            None,
            threshold,
            f"Needs sleep logged on at least {MIN_REPORTED_DAYS} of the last 7 nights "
            f"(found {nights}).",
        )
    avg = wellness.avg_sleep_hours
    status: FlagStatus = "triggered" if avg < threshold else "not_triggered"
    relation = "below" if status == "triggered" else "at or above"
    return Flag(
        code,
        status,
        avg,
        threshold,
        f"Average reported sleep was {avg:.1f} h over {nights} nights, {relation} the "
        f"{threshold:.0f} h heuristic threshold.",
    )


def evaluate_flags(load: LoadMetrics, wellness: Wellness) -> list[Flag]:
    return [
        weekly_load_jump(load),
        acwr_spike(load),
        sustained_fatigue(wellness),
        short_sleep(wellness),
    ]


def overall_status(flags: list[Flag]) -> str:
    evaluated = [f for f in flags if f.status != "insufficient_data"]
    if not evaluated:
        return "insufficient_data"
    triggered = sum(1 for f in evaluated if f.status == "triggered")
    if triggered == 0:
        return "no_flags"
    return "caution" if triggered == 1 else "elevated"
