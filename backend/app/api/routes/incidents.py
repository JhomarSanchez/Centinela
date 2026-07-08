"""Incident listing endpoints (read-only: incidents are created by the scheduler)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.models import Incident
from app.models.schemas import IncidentRead
from app.services import incident_manager

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
def list_incidents(
    db: DbSession,
    active: Annotated[
        bool | None,
        Query(description="true = only open incidents, false = only resolved, omit = all"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[Incident]:
    return incident_manager.list_incidents(db, active=active, limit=limit)
