"""Daily wellness check-in endpoint."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Path

from app.api.dependencies import CheckInServiceDep
from app.core.auth import CurrentUserDep
from app.core.errors import ValidationAppError
from app.schemas.checkins import CheckInOut, CheckInPut
from app.schemas.common import check_date_in_range

router = APIRouter(prefix="/checkins", tags=["checkins"])


@router.put("/{checkin_date}", response_model=CheckInOut)
def put_checkin(
    checkin_date: Annotated[date, Path(description="Local calendar date, YYYY-MM-DD")],
    payload: Annotated[CheckInPut, Body()],
    user: CurrentUserDep,
    service: CheckInServiceDep,
) -> CheckInOut:
    try:
        check_date_in_range(checkin_date)
    except ValueError as exc:
        raise ValidationAppError(
            "Invalid date.", [{"field": "checkin_date", "issue": str(exc)}]
        ) from exc
    return service.put(user.user_id, checkin_date, payload)
