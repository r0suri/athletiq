"""Workout identifiers.

A workout id is "<yyyy-mm-dd>_<ULID>", e.g. "2026-10-27_01JB7Q8Z1T3XK9V2M4N6P8R0SA".
The date lets the API rebuild the exact DynamoDB sort key (no index needed); the ULID
(time-ordered, 80 random bits) keeps several workouts on the same day unique and in
creation order. Clients should treat the id as opaque.
"""

import os
import re
import time
from datetime import date

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ULID = r"[0-9A-HJKMNP-TV-Z]{26}"
_WORKOUT_ID = re.compile(rf"^(\d{{4}}-\d{{2}}-\d{{2}})_({_ULID})$")


def new_ulid(timestamp_ms: int | None = None, randomness: bytes | None = None) -> str:
    """48-bit millisecond timestamp + 80 random bits, Crockford base32 (26 chars)."""
    ms = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    rand = os.urandom(10) if randomness is None else randomness
    value = (ms << 80) | int.from_bytes(rand, "big")
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(chars))


def make_workout_id(workout_date: date, ulid: str) -> str:
    return f"{workout_date.isoformat()}_{ulid}"


def parse_workout_id(workout_id: str) -> tuple[date, str] | None:
    """Return (date, ulid), or None if the id is malformed."""
    match = _WORKOUT_ID.fullmatch(workout_id)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1)), match.group(2)
    except ValueError:  # e.g. 2026-02-30
        return None
