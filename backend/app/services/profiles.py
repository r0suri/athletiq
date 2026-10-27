"""Profile use cases. Users without a saved profile get explicit defaults."""

from collections.abc import Callable
from datetime import UTC, datetime

from app.repositories.profiles import ProfileRepository, StoredProfile
from app.schemas.profile import DEFAULT_GOAL, DEFAULT_TIMEZONE, ProfileOut, ProfilePut


def default_profile() -> ProfileOut:
    return ProfileOut(
        goal=DEFAULT_GOAL, timezone=DEFAULT_TIMEZONE, configured=False, updated_at=None
    )


class ProfileService:
    def __init__(
        self, repo: ProfileRepository, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._repo = repo
        self._clock = clock

    def get(self, user_id: str) -> ProfileOut:
        # No write on read: a missing profile is reported, not silently created.
        stored = self._repo.get(user_id)
        if stored is None:
            return default_profile()
        return ProfileOut(
            goal=stored.goal,
            timezone=stored.timezone,
            configured=True,
            updated_at=stored.updated_at,
        )

    def put(self, user_id: str, payload: ProfilePut) -> ProfileOut:
        stored = StoredProfile(
            goal=payload.goal, timezone=payload.timezone, updated_at=self._clock()
        )
        self._repo.put(user_id, stored)
        return ProfileOut(
            goal=stored.goal,
            timezone=stored.timezone,
            configured=True,
            updated_at=stored.updated_at,
        )
