"""Incident listing endpoints (read-only: incidents are created by the scheduler)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.ai.providers import ProviderError
from app.ai.worker import retry_summary
from app.api.deps import DbSession, require_auth, require_write_auth
from app.models import Incident
from app.models.schemas import IncidentContextRead, IncidentDetailRead, IncidentRead
from app.services import incident_manager

router = APIRouter(
    prefix="/incidents",
    tags=["incidents"],
    dependencies=[Depends(require_auth)],
)


def _get_incident_or_404(incident_id: int, db: DbSession) -> Incident:
    incident = incident_manager.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


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


@router.get("/{incident_id}", response_model=IncidentDetailRead)
def get_incident(incident_id: int, db: DbSession) -> IncidentDetailRead:
    incident = _get_incident_or_404(incident_id, db)
    return IncidentDetailRead.model_validate(
        {
            **IncidentRead.model_validate(incident).model_dump(),
            "service_name": incident.service.name,
        }
    )


@router.get("/{incident_id}/context", response_model=IncidentContextRead)
def get_incident_context(incident_id: int, db: DbSession) -> IncidentContextRead:
    incident = _get_incident_or_404(incident_id, db)
    return IncidentContextRead(incident_id=incident.id, raw_context=incident.raw_context)


@router.post(
    "/{incident_id}/ai/retry",
    response_model=IncidentRead,
    dependencies=[Depends(require_write_auth)],
)
def retry_incident_summary(incident_id: int, db: DbSession) -> Incident:
    incident = _get_incident_or_404(incident_id, db)
    try:
        return retry_summary(db, incident)
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"AI provider is not ready: {exc.code.value}",
        ) from None
