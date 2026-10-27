"""Training analytics for the authenticated user."""

from fastapi import APIRouter

from app.api.dependencies import AnalyticsServiceDep
from app.core.auth import CurrentUserDep
from app.schemas.analytics import AnalyticsSummaryOut

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryOut)
def get_summary(user: CurrentUserDep, service: AnalyticsServiceDep) -> AnalyticsSummaryOut:
    """Heuristic training-load summary. Not medical advice; see `disclaimer`."""
    return service.summary(user.user_id)
