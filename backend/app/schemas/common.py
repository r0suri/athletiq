"""Shared validation helpers for API schemas."""

from datetime import UTC, date, datetime, timedelta

EARLIEST_DATE = date(2000, 1, 1)


def latest_allowed_date() -> date:
    """Today in UTC plus one day, so users in any timezone can log 'today'."""
    return datetime.now(UTC).date() + timedelta(days=1)


def check_date_in_range(value: date) -> date:
    if value < EARLIEST_DATE:
        raise ValueError(f"date must be on or after {EARLIEST_DATE.isoformat()}")
    if value > latest_allowed_date():
        raise ValueError("date cannot be in the future")
    return value
