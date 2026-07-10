"""Service CRUD and check-history endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, require_auth, require_write_auth
from app.models import Check, Incident, Service
from app.models.schemas import (
    CheckRead,
    IncidentRead,
    ServiceCreate,
    ServiceRead,
    ServiceSummary,
    ServiceTimelineRead,
    ServiceUpdate,
)
from app.services import incident_manager, service_manager
from app.services.check_runner import execute_check
from app.services.service_manager import ServiceNameTakenError

router = APIRouter(
    prefix="/services",
    tags=["services"],
    dependencies=[Depends(require_auth)],
)


def _get_service_or_404(service_id: int, db: DbSession) -> Service:
    service = service_manager.get_service(db, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.post(
    "",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_auth)],
)
def create_service(payload: ServiceCreate, db: DbSession) -> Service:
    try:
        return service_manager.create_service(db, payload)
    except ServiceNameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A service named '{payload.name}' already exists",
        ) from None


@router.get("", response_model=list[ServiceSummary])
def list_services(db: DbSession) -> list[ServiceSummary]:
    return service_manager.list_service_summaries(db)


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: DbSession) -> Service:
    return _get_service_or_404(service_id, db)


@router.patch(
    "/{service_id}",
    response_model=ServiceRead,
    dependencies=[Depends(require_write_auth)],
)
def update_service(service_id: int, payload: ServiceUpdate, db: DbSession) -> Service:
    service = _get_service_or_404(service_id, db)
    try:
        return service_manager.update_service(db, service, payload)
    except ServiceNameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A service named '{payload.name}' already exists",
        ) from None


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_auth)],
)
def delete_service(service_id: int, db: DbSession) -> None:
    service = _get_service_or_404(service_id, db)
    service_manager.delete_service(db, service)


@router.get("/{service_id}/checks", response_model=list[CheckRead])
def list_checks(
    service_id: int,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[Check]:
    _get_service_or_404(service_id, db)
    return service_manager.list_checks(db, service_id, limit=limit)


@router.post(
    "/{service_id}/checks/run",
    response_model=CheckRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_auth)],
)
def run_service_check(service_id: int, db: DbSession) -> Check:
    """Run one immediate check through the same path as the scheduler."""
    service = _get_service_or_404(service_id, db)
    return execute_check(db, service)


@router.get("/{service_id}/timeline", response_model=ServiceTimelineRead)
def get_service_timeline(
    service_id: int,
    db: DbSession,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    bucket: Annotated[Literal["5m", "1h", "1d"], Query()] = "1h",
) -> ServiceTimelineRead:
    _get_service_or_404(service_id, db)
    end = to or datetime.now(UTC)
    start = from_ or end - timedelta(hours=24)
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    if start >= end:
        raise HTTPException(status_code=422, detail="'from' must be before 'to'")
    if end - start > timedelta(days=30):
        raise HTTPException(status_code=422, detail="Timeline range cannot exceed 30 days")
    return service_manager.service_timeline(db, service_id, start, end, bucket)


@router.get("/{service_id}/incidents", response_model=list[IncidentRead])
def list_service_incidents(
    service_id: int,
    db: DbSession,
    active: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[Incident]:
    _get_service_or_404(service_id, db)
    return incident_manager.list_incidents(db, service_id=service_id, active=active, limit=limit)
