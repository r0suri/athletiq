"""Profile persistence: one item per user, SK = PROFILE."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.domain.models import Goal
from app.repositories.dynamodb import user_pk

PROFILE_SK = "PROFILE"


@dataclass(frozen=True)
class StoredProfile:
    goal: Goal
    timezone: str
    updated_at: datetime


class ProfileRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    def get(self, user_id: str) -> StoredProfile | None:
        item = self._table.get_item(Key={"PK": user_pk(user_id), "SK": PROFILE_SK}).get("Item")
        if not item:
            return None
        return StoredProfile(
            goal=Goal(item["goal"]),
            timezone=item["timezone"],
            updated_at=datetime.fromisoformat(item["updated_at"]),
        )

    def put(self, user_id: str, profile: StoredProfile) -> None:
        self._table.put_item(
            Item={
                "PK": user_pk(user_id),
                "SK": PROFILE_SK,
                "entity": "PROFILE",
                "goal": profile.goal.value,
                "timezone": profile.timezone,
                "updated_at": profile.updated_at.isoformat(),
            }
        )
