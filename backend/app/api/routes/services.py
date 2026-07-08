"""Service CRUD and check-history endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, require_api_key
from app.models import Check, Incident, Service
from app.models.schemas import CheckRead, IncidentRead, ServiceCreate, ServiceRead, ServiceUpdate
from app.services import incident_manager, service_manager
from app.services.service_manager import ServiceNameTakenError

router = APIRouter(prefix="/services", tags=["services"])


def _get_service_or_404(service_id: int, db: DbSession) -> Service:
    service = service_manager.get_service(db, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.post(
    "",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_service(payload: ServiceCreate, db: DbSession) -> Service:
    try:
        return service_manager.create_service(db, payload)
    except ServiceNameTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A service named '{payload.name}' already exists",
        ) from None


@router.get("", response_model=list[ServiceRead])
def list_services(db: DbSession) -> list[Service]:
    return service_manager.list_services(db)


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: DbSession) -> Service:
    return _get_service_or_404(service_id, db)


@router.patch(
    "/{service_id}",
    response_model=ServiceRead,
    dependencies=[Depends(require_api_key)],
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
    dependencies=[Depends(require_api_key)],
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


@router.get("/{service_id}/incidents", response_model=list[IncidentRead])
def list_service_incidents(
    service_id: int,
    db: DbSession,
    active: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[Incident]:
    _get_service_or_404(service_id, db)
    return incident_manager.list_incidents(db, service_id=service_id, active=active, limit=limit)
