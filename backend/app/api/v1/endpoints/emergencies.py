"""Endpoints de Urgencias Médicas, Despacho SOS, Escalamiento y Torre de Control (plan/plan.md 2.B.7)."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.acl import Permission
from app.core.database import get_db
from app.core.emergency_hub import emergency_hub
from app.models.user import User
from app.schemas.emergency import (
    EmergencyIncidentPublic,
    EmergencyResolveRequest,
    EmergencySosRequest,
    NotificationLogPublic,
)
from app.services.emergency_service import EmergencyService

router = APIRouter()


@router.post(
    "/sos",
    response_model=EmergencyIncidentPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Disparar Alerta SOS de Urgencia Médica",
)
async def trigger_sos(
    payload: EmergencySosRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.EMERGENCY_TRIGGER))],
):
    """Dispara un evento de urgencia médica con validación estricta de descargo legal previo."""
    service = EmergencyService(db)
    return await service.trigger_sos(current_user, payload)


@router.get(
    "/active",
    response_model=list[EmergencyIncidentPublic],
    summary="Listar incidentes activos para Torre de Control",
)
async def list_active_emergencies(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.EMERGENCY_MONITOR))],
    clinic_id: str | None = None,
):
    """Consulta la lista de urgencias activas en tiempo real."""
    if current_user.role == "CLINIC_ADMIN":
        clinic_id = current_user.clinic_id

    service = EmergencyService(db)
    return await service.get_active_incidents(clinic_id=clinic_id)


@router.get(
    "/my",
    response_model=list[EmergencyIncidentPublic],
    summary="Listar mis incidentes SOS reportados",
)
async def list_my_emergencies(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = EmergencyService(db)
    return await service.get_patient_incidents(patient_id=current_user.id)


@router.post(
    "/{incident_id}/accept",
    response_model=EmergencyIncidentPublic,
    summary="Médico de guardia acepta y toma el caso SOS",
)
async def accept_emergency(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.EMERGENCY_RESPOND))],
):
    service = EmergencyService(db)
    return await service.accept_incident(incident_id, current_user)


@router.post(
    "/{incident_id}/escalate",
    response_model=EmergencyIncidentPublic,
    summary="Avanzar nivel de escalamiento en cadena multicanal",
)
async def escalate_emergency(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.EMERGENCY_MONITOR))],
):
    service = EmergencyService(db)
    return await service.escalate_incident(incident_id)


@router.post(
    "/{incident_id}/resolve",
    response_model=EmergencyIncidentPublic,
    summary="Finalizar incidente con notas de triaje médico",
)
async def resolve_emergency(
    incident_id: str,
    payload: EmergencyResolveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.EMERGENCY_RESPOND))],
):
    service = EmergencyService(db)
    return await service.resolve_incident(incident_id, current_user, payload)


@router.get(
    "/{incident_id}/audit-timeline",
    response_model=list[NotificationLogPublic],
    summary="Línea de tiempo y auditoría de notificaciones del incidente",
)
async def get_incident_audit_timeline(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    service = EmergencyService(db)
    incident = await service.repo.get_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incidente no encontrado.")

    # Control de acceso: el paciente dueño o personal con permisos de monitoreo/respuesta
    if current_user.role == "PATIENT" and incident.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado para ver este incidente.")

    return await service.get_incident_audit_logs(incident_id)


@router.websocket("/ws/control-tower")
async def control_tower_websocket(websocket: WebSocket):
    """Canal WebSocket bidireccional para monitoreo en tiempo real de la Torre de Control."""
    await emergency_hub.connect(websocket)
    try:
        while True:
            # Mantener conexión activa y recibir pings/mensajes de clientes
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        emergency_hub.disconnect(websocket)
    except Exception:
        emergency_hub.disconnect(websocket)
