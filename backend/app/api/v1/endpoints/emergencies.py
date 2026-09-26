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
    EmergencyAssignRequest,
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
    return await service.escalate_incident(incident_id, automatic=False)


@router.post(
    "/{incident_id}/acknowledge",
    response_model=EmergencyIncidentPublic,
    summary="Moderador de turno reconoce el incidente (SLA de 2 minutos)",
)
async def acknowledge_emergency(
    incident_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.EMERGENCY_MONITOR))],
):
    service = EmergencyService(db)
    return await service.acknowledge_incident(incident_id, current_user)


@router.post(
    "/{incident_id}/assign",
    response_model=EmergencyIncidentPublic,
    summary="Asignación manual de un médico disponible desde la Torre de Control",
)
async def assign_emergency_doctor(
    incident_id: str,
    payload: EmergencyAssignRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.EMERGENCY_MONITOR))],
):
    service = EmergencyService(db)
    return await service.assign_doctor(incident_id, payload.doctor_id, current_user)


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

    # Control de acceso: el paciente dueño, el médico asignado o contactado,
    # y el personal con permiso de monitoreo (Torre de Control).
    from app.core.acl import has_permission

    contacted = {log.recipient_id for log in incident.notification_logs or [] if log.recipient_id}
    allowed = (
        (current_user.role == "PATIENT" and incident.patient_id == current_user.id)
        or (current_user.role == "DOCTOR" and (incident.assigned_doctor_id == current_user.id or current_user.id in contacted))
        or (
            has_permission(current_user.role, Permission.EMERGENCY_MONITOR)
            and (current_user.role != "CLINIC_ADMIN" or incident.clinic_id == current_user.clinic_id)
        )
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="No autorizado para ver este incidente.")

    return await service.get_incident_audit_logs(incident_id)


@router.websocket("/ws/control-tower")
async def control_tower_websocket(websocket: WebSocket, token: str | None = Query(None)):
    """Canal WebSocket de la Torre de Control.

    Exige un access token válido (query `token`, los navegadores no permiten
    cabeceras en WebSocket) de un usuario ACTIVO con permiso
    `emergency:monitor`: los eventos incluyen datos de salud del paciente.
    """
    from app.core.acl import has_permission
    from app.core.database import AsyncSessionLocal
    from app.core.tenant import GLOBAL_ROLES
    from app.core.security import decode_token
    from app.repositories.user_repository import UserRepository

    authorized = False
    if token:
        try:
            payload = decode_token(token)
            if payload.get("type") == "access":
                async with AsyncSessionLocal() as session:
                    user = await UserRepository(session).get_by_id(payload["sub"])
                # Solo staff global: el canal difunde incidentes de TODAS las
                # clinicas. Los CLINIC_ADMIN consultan /emergencies/active,
                # que si filtra por su sede.
                authorized = bool(
                    user
                    and user.status == "ACTIVE"
                    and user.role in GLOBAL_ROLES
                    and has_permission(user.role, Permission.EMERGENCY_MONITOR)
                )
        except Exception:  # noqa: BLE001
            authorized = False
    if not authorized:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await emergency_hub.connect(websocket)
    try:
        while True:
            # Mantener conexión activa y recibir pings/mensajes de clientes
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        emergency_hub.disconnect(websocket)
    except Exception:
        emergency_hub.disconnect(websocket)
