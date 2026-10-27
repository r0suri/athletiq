"""Daily check-in use cases."""

from collections.abc import Callable
from datetime import UTC, date, datetime

from app.domain.models import DailyCheckIn
from app.repositories.checkins import CheckInRepository
from app.schemas.checkins import CheckInOut, CheckInPut


class CheckInService:
    def __init__(
        self, repo: CheckInRepository, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._repo = repo
        self._clock = clock

    def put(self, user_id: str, checkin_date: date, payload: CheckInPut) -> CheckInOut:
        now = self._clock()
        checkin = DailyCheckIn(
            checkin_date=checkin_date,
            sleep_hours=payload.sleep_hours,
            fatigue=payload.fatigue,
            soreness=payload.soreness,
        )
        self._repo.put(user_id, checkin, updated_at=now)
        return CheckInOut(
            date=checkin_date,
            sleep_hours=payload.sleep_hours,
            fatigue=payload.fatigue,
            soreness=payload.soreness,
            updated_at=now,
        )
