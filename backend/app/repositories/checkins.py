"""Daily check-in persistence: one item per user per date, SK = CHECKIN#<date>."""

from collections.abc import Iterator
from datetime import date, datetime
from typing import Any

from boto3.dynamodb.conditions import Key

from app.domain.models import DailyCheckIn
from app.repositories.dynamodb import from_dynamo, to_dynamo, user_pk

SK_PREFIX = "CHECKIN#"


class CheckInRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def put(self, user_id: str, checkin: DailyCheckIn, updated_at: datetime) -> None:
        """Create or fully replace the check-in for that date (PUT semantics)."""
        item = {
            "PK": user_pk(user_id),
            "SK": f"{SK_PREFIX}{checkin.checkin_date.isoformat()}",
            "entity": "CHECKIN",
            "date": checkin.checkin_date.isoformat(),
            "sleep_hours": checkin.sleep_hours,
            "fatigue": checkin.fatigue,
            "soreness": checkin.soreness,
            "updated_at": updated_at.isoformat(),
        }
        self._table.put_item(Item=to_dynamo(item))  # None fields are omitted

    def iter_range(self, user_id: str, start: date, end: date) -> Iterator[DailyCheckIn]:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("PK").eq(user_pk(user_id))
            & Key("SK").between(f"{SK_PREFIX}{start.isoformat()}", f"{SK_PREFIX}{end.isoformat()}")
        }
        while True:
            response = self._table.query(**kwargs)
            for raw in response.get("Items", []):
                item = from_dynamo(raw)
                yield DailyCheckIn(
                    checkin_date=date.fromisoformat(item["date"]),
                    sleep_hours=item.get("sleep_hours"),
                    fatigue=item.get("fatigue"),
                    soreness=item.get("soreness"),
                )
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                return
            kwargs["ExclusiveStartKey"] = last_key
