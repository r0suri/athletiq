"""Workout persistence. All methods take the authenticated user_id and build the
partition key from it, so a caller cannot address another user's items."""

import base64
import binascii
import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from app.domain.ids import parse_workout_id
from app.domain.models import StrengthSet, WorkoutRecord, WorkoutType
from app.repositories.dynamodb import from_dynamo, to_dynamo, user_pk

SK_PREFIX = "WORKOUT#"
SK_HIGH = "~"  # sorts after every ULID character, so "<date>#~" ends that date's range


class InvalidCursorError(ValueError):
    pass


@dataclass(frozen=True)
class StoredWorkout:
    workout_id: str
    record: WorkoutRecord
    notes: str | None
    source: str
    created_at: datetime


def workout_sk(workout_id: str) -> str | None:
    parsed = parse_workout_id(workout_id)
    if parsed is None:
        return None
    workout_date, ulid = parsed
    return f"{SK_PREFIX}{workout_date.isoformat()}#{ulid}"


def _encode_cursor(sk: str) -> str:
    # Only the sort key goes in the cursor. The partition key always comes from the
    # authenticated user, so a tampered cursor cannot reach another user's data.
    return base64.urlsafe_b64encode(json.dumps({"sk": sk}).encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> str:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        sk = json.loads(base64.urlsafe_b64decode(padded.encode()))["sk"]
    except (binascii.Error, ValueError, KeyError, TypeError) as exc:
        raise InvalidCursorError("cursor is malformed") from exc
    if not isinstance(sk, str) or not sk.startswith(SK_PREFIX):
        raise InvalidCursorError("cursor is malformed")
    return sk


def _to_item(user_id: str, w: StoredWorkout, load: float) -> dict[str, Any]:
    r = w.record
    item = {
        "PK": user_pk(user_id),
        "SK": workout_sk(w.workout_id),
        "entity": "WORKOUT",
        "workout_id": w.workout_id,
        "workout_type": r.workout_type.value,
        "date": r.workout_date.isoformat(),
        "duration_min": r.duration_min,
        "rpe": r.rpe,
        "load": load,
        "distance_km": r.distance_km,
        "exercises": [
            {"name": s.exercise, "sets": s.sets, "reps": s.reps, "weight_kg": s.weight_kg}
            for s in r.exercises
        ],
        "notes": w.notes,
        "source": w.source,
        "created_at": w.created_at.isoformat(),
    }
    return to_dynamo(item)


def _from_item(raw: dict[str, Any]) -> StoredWorkout:
    item = from_dynamo(raw)
    record = WorkoutRecord(
        workout_date=date.fromisoformat(item["date"]),
        workout_type=WorkoutType(item["workout_type"]),
        duration_min=float(item["duration_min"]),
        rpe=int(item["rpe"]),
        distance_km=float(item["distance_km"]) if "distance_km" in item else None,
        exercises=tuple(
            StrengthSet(e["name"], int(e["sets"]), int(e["reps"]), float(e.get("weight_kg", 0)))
            for e in item.get("exercises", [])
        ),
    )
    return StoredWorkout(
        workout_id=item["workout_id"],
        record=record,
        notes=item.get("notes"),
        source=item.get("source", "manual"),
        created_at=datetime.fromisoformat(item["created_at"]),
    )


class WorkoutRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def put(self, user_id: str, workout: StoredWorkout, load: float) -> None:
        self._table.put_item(
            Item=_to_item(user_id, workout, load),
            ConditionExpression="attribute_not_exists(PK)",  # never silently overwrite
        )

    def get(self, user_id: str, workout_id: str) -> StoredWorkout | None:
        sk = workout_sk(workout_id)
        if sk is None:
            return None
        response = self._table.get_item(Key={"PK": user_pk(user_id), "SK": sk})
        item = response.get("Item")
        return _from_item(item) if item else None

    def delete(self, user_id: str, workout_id: str) -> bool:
        """Delete and return True, or return False if the user has no such workout."""
        sk = workout_sk(workout_id)
        if sk is None:
            return False
        try:
            self._table.delete_item(
                Key={"PK": user_pk(user_id), "SK": sk},
                ConditionExpression="attribute_exists(SK)",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def list_page(
        self,
        user_id: str,
        start: date,
        end: date,
        limit: int,
        cursor: str | None = None,
        workout_type: WorkoutType | None = None,
    ) -> tuple[list[StoredWorkout], str | None]:
        """Newest-first page of workouts dated start..end (inclusive)."""
        key = Key("PK").eq(user_pk(user_id)) & Key("SK").between(
            f"{SK_PREFIX}{start.isoformat()}", f"{SK_PREFIX}{end.isoformat()}#{SK_HIGH}"
        )
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": key,
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if workout_type is not None:
            # Filters are applied after the key-range read, so we may need several
            # pages to collect `limit` matches. The read is still bounded by the range.
            kwargs["FilterExpression"] = Attr("workout_type").eq(workout_type.value)
        if cursor:
            kwargs["ExclusiveStartKey"] = {"PK": user_pk(user_id), "SK": _decode_cursor(cursor)}

        results: list[StoredWorkout] = []
        while True:
            response = self._table.query(**kwargs)
            items = response.get("Items", [])
            for index, raw in enumerate(items):
                results.append(_from_item(raw))
                if len(results) == limit:
                    more = index < len(items) - 1 or "LastEvaluatedKey" in response
                    return results, (_encode_cursor(raw["SK"]) if more else None)
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                return results, None
            kwargs["ExclusiveStartKey"] = last_key

    def iter_range(self, user_id: str, start: date, end: date) -> Iterator[StoredWorkout]:
        """Every workout dated start..end, oldest first (used by analytics)."""
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(user_pk(user_id))
            & Key("SK").between(
                f"{SK_PREFIX}{start.isoformat()}", f"{SK_PREFIX}{end.isoformat()}#{SK_HIGH}"
            )
        }
        while True:
            response = self._table.query(**kwargs)
            for raw in response.get("Items", []):
                yield _from_item(raw)
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                return
            kwargs["ExclusiveStartKey"] = last_key
