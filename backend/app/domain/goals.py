"""Goal-specific progress summaries built from deterministic templates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.models import Goal

if TYPE_CHECKING:
    from app.domain.analytics import WeekVolume

GOAL_TARGET_SESSIONS: dict[Goal, int] = {
    Goal.STRENGTH: 3,
    Goal.ENDURANCE: 4,
    Goal.GENERAL_FITNESS: 3,
}
ACTIVE_MINUTES_REFERENCE = 150  # widely cited weekly public-health reference


@dataclass(frozen=True)
class GoalSummary:
    goal: Goal
    headline: str
    metrics: dict[str, float | None]


def _change_text(current: float, previous: float) -> str:
    if previous <= 0:
        return "no previous-week data to compare"
    return f"{(current - previous) / previous * 100:+.1f}% vs previous 7 days"


def build_goal_summary(goal: Goal, current: WeekVolume, previous: WeekVolume) -> GoalSummary:
    if goal is Goal.ENDURANCE:
        km = current.run_distance_km + current.ride_distance_km
        prev_km = previous.run_distance_km + previous.ride_distance_km
        sessions = current.sessions_by_type["run"] + current.sessions_by_type["ride"]
        headline = (
            f"Endurance: {km:.1f} km across {sessions} run/ride sessions in the last 7 days "
            f"({_change_text(km, prev_km)})."
        )
        metrics = {
            "endurance_distance_km": km,
            "previous_endurance_distance_km": prev_km,
            "endurance_sessions": float(sessions),
            "target_sessions": float(GOAL_TARGET_SESSIONS[goal]),
        }
    elif goal is Goal.STRENGTH:
        sessions = current.sessions_by_type["strength"]
        target = GOAL_TARGET_SESSIONS[goal]
        headline = f"Strength: {sessions} of {target} target strength sessions in the last 7 days"
        if current.strength_tonnage_kg > 0:
            headline += f", {current.strength_tonnage_kg:,.0f} kg total volume lifted"
        headline += "."
        metrics = {
            "strength_sessions": float(sessions),
            "target_sessions": float(target),
            "strength_tonnage_kg": current.strength_tonnage_kg or None,
            "previous_strength_tonnage_kg": previous.strength_tonnage_kg or None,
        }
    else:
        minutes = current.duration_min
        types = sum(1 for n in current.sessions_by_type.values() if n > 0)
        headline = (
            f"General fitness: {minutes:.0f} active minutes in the last 7 days "
            f"(reference: {ACTIVE_MINUTES_REFERENCE} min/week) across {types} activity type"
            f"{'' if types == 1 else 's'}."
        )
        metrics = {
            "active_minutes": minutes,
            "reference_minutes": float(ACTIVE_MINUTES_REFERENCE),
            "activity_types": float(types),
        }
    return GoalSummary(goal=goal, headline=headline, metrics=metrics)
