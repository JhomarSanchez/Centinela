"""Product overview endpoint."""

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_auth
from app.models.schemas import DashboardSummaryRead
from app.services.dashboard_manager import dashboard_summary

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_auth)],
)


@router.get("/summary", response_model=DashboardSummaryRead)
def get_dashboard_summary(db: DbSession) -> DashboardSummaryRead:
    return dashboard_summary(db)
