"""Workout use cases: the layer between HTTP routes and the repository.

Routes handle HTTP concerns; this service owns business rules (id generation,
load calculation, default date ranges); the repository owns DynamoDB details.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from app.core.errors import NotFoundError, ValidationAppError
from app.domain.analytics import session_load
from app.domain.ids import make_workout_id, new_ulid
from app.domain.models import StrengthSet, WorkoutRecord, WorkoutType
from app.repositories.workouts import InvalidCursorError, StoredWorkout, WorkoutRepository
from app.schemas.workouts import (
    ExerciseOut,
    RideCreate,
    RunCreate,
    StrengthCreate,
    WorkoutList,
    WorkoutOut,
)

DEFAULT_LIST_DAYS = 90


def to_out(w: StoredWorkout) -> WorkoutOut:
    r = w.record
    return WorkoutOut(
        id=w.workout_id,
        type=r.workout_type.value,
        date=r.workout_date,
        duration_min=r.duration_min,
        rpe=r.rpe,
        load=session_load(r),
        distance_km=r.distance_km,
        exercises=[
            ExerciseOut(name=s.exercise, sets=s.sets, reps=s.reps, weight_kg=s.weight_kg)
            for s in r.exercises
        ],
        notes=w.notes,
        source=w.source,
        created_at=w.created_at,
    )


class WorkoutService:
    def __init__(
        self, repo: WorkoutRepository, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._repo = repo
        self._clock = clock

    def create(self, user_id: str, payload: RunCreate | RideCreate | StrengthCreate) -> WorkoutOut:
        now = self._clock()
        exercises: tuple[StrengthSet, ...] = ()
        distance = None
        if isinstance(payload, StrengthCreate):
            exercises = tuple(
                StrengthSet(e.name, e.sets, e.reps, e.weight_kg) for e in payload.exercises
            )
        else:
            distance = payload.distance_km
        record = WorkoutRecord(
            workout_date=payload.date,
            workout_type=WorkoutType(payload.type),
            duration_min=payload.duration_min,
            rpe=payload.rpe,
            distance_km=distance,
            exercises=exercises,
        )
        stored = StoredWorkout(
            workout_id=make_workout_id(payload.date, new_ulid(int(now.timestamp() * 1000))),
            record=record,
            notes=payload.notes,
            source="manual",
            created_at=now,
        )
        self._repo.put(user_id, stored, load=session_load(record))
        return to_out(stored)

    def get(self, user_id: str, workout_id: str) -> WorkoutOut:
        stored = self._repo.get(user_id, workout_id)
        if stored is None:
            # Same response whether the id is malformed, missing or another user's:
            # we never reveal that someone else's workout exists.
            raise NotFoundError("Workout not found.")
        return to_out(stored)

    def delete(self, user_id: str, workout_id: str) -> None:
        if not self._repo.delete(user_id, workout_id):
            raise NotFoundError("Workout not found.")

    def list(
        self,
        user_id: str,
        start: date | None,
        end: date | None,
        limit: int,
        cursor: str | None,
        workout_type: WorkoutType | None,
    ) -> WorkoutList:
        today = self._clock().date()
        end = end or today + timedelta(days=1)
        start = start or end - timedelta(days=DEFAULT_LIST_DAYS)
        if start > end:
            raise ValidationAppError(
                "Invalid date range.", [{"field": "from", "issue": "must be on or before 'to'"}]
            )
        try:
            items, next_cursor = self._repo.list_page(
                user_id, start, end, limit, cursor, workout_type
            )
        except InvalidCursorError as exc:
            raise ValidationAppError(
                "Invalid cursor.", [{"field": "cursor", "issue": str(exc)}]
            ) from exc
        return WorkoutList(items=[to_out(w) for w in items], next_cursor=next_cursor)
