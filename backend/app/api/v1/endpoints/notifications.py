"""Endpoints de gestión de preferencias y consulta de logs de notificaciones multicanal (plan/plan.md Módulo 6)."""

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.repositories.device_token_repository import DeviceTokenRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import (
    DeviceTokenRegisterRequest,
    DeviceTokenResponse,
    InAppNotificationSummary,
    NotificationLogPublic,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)

router = APIRouter()



@router.get("/my-preferences", response_model=NotificationPreferenceResponse, summary="Obtener preferencias de notificación del usuario actual")
async def get_my_notification_preferences(
    current_user: User = Depends(get_current_user),
):
    """Devuelve los canales preferidos de notificación del usuario autenticado."""
    channels = current_user.preferred_notification_channels or ["PUSH", "WHATSAPP", "EMAIL"]
    return NotificationPreferenceResponse(
        user_id=current_user.id,
        preferred_notification_channels=channels,
        has_whatsapp=bool(current_user.phone),
        fallback_channels=["PUSH", "SMS", "VOICE_CALL", "EMAIL"],
    )


@router.put("/my-preferences", response_model=NotificationPreferenceResponse, summary="Actualizar canales preferidos de notificación")
async def update_my_notification_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permite al usuario (paciente o médico) seleccionar sus canales preferidos."""
    if not payload.preferred_notification_channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe seleccionar al menos un canal de notificación.",
        )

    current_user.preferred_notification_channels = [ch.upper() for ch in payload.preferred_notification_channels]
    await db.commit()
    await db.refresh(current_user)

    return NotificationPreferenceResponse(
        user_id=current_user.id,
        preferred_notification_channels=current_user.preferred_notification_channels,
        has_whatsapp=bool(current_user.phone),
        fallback_channels=["PUSH", "SMS", "VOICE_CALL", "EMAIL"],
    )


@router.post("/devices", response_model=DeviceTokenResponse, summary="Registrar token FCM de dispositivo")
async def register_device_token(
    payload: DeviceTokenRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra o actualiza el token FCM de un dispositivo (móvil o navegador) asociado al usuario."""
    repo = DeviceTokenRepository(db)
    token = await repo.register_device_token(
        user_id=current_user.id,
        fcm_token=payload.fcm_token,
        platform=payload.platform,
        device_name=payload.device_name,
    )
    await db.commit()
    await db.refresh(token)
    return token


@router.get("/devices", response_model=list[DeviceTokenResponse], summary="Listar dispositivos registrados")
async def list_my_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los dispositivos registrados del usuario actual."""
    repo = DeviceTokenRepository(db)
    return await repo.get_all_tokens_for_user(current_user.id)


@router.delete("/devices/{identifier}", summary="Desvincular o eliminar dispositivo")
async def delete_device(
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Elimina o desvincula un dispositivo por ID o por token FCM."""
    repo = DeviceTokenRepository(db)
    deleted = await repo.remove_device(current_user.id, identifier)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dispositivo no encontrado o no pertenece al usuario",
        )
    await db.commit()
    return {"message": "Dispositivo desvinculado con éxito"}


@router.post("/test-send", summary="Enviar notificación de prueba multicanal e in-app")
async def send_test_notification(
    subject: str = Query("Prueba de Notificación", description="Título"),
    message: str = Query("Esta es una notificación de prueba en tiempo real desde ÍntimaSalud.", description="Mensaje"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permite disparar una notificación de prueba al usuario actual para verificar In-App, Email y logs."""
    from app.services.notification_service import NotificationService
    service = NotificationService(db)
    logs = await service.send_multichannel_notification(
        recipient=current_user,
        subject=subject,
        message=message,
        metadata_payload={"type": "TEST_NOTIFICATION"},
    )
    return {
        "status": "dispatched",
        "channels_sent": [l.channel for l in logs],
        "logs_count": len(logs),
    }


@router.get("/logs", response_model=list[NotificationLogPublic], summary="Consultar logs de auditoría de entrega de notificaciones")
async def get_notification_logs(

    appointment_id: str | None = Query(None, description="ID de la cita médica"),
    incident_id: str | None = Query(None, description="ID del incidente de urgencia"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permite consultar el historial inmutable de intentos de notificación."""
    repo = NotificationRepository(db)

    if appointment_id:
        logs = await repo.list_by_appointment(appointment_id)
    elif incident_id:
        logs = await repo.list_by_incident(incident_id)
    else:
        # Por defecto los logs del usuario actual
        logs = await repo.list_by_recipient(current_user.id)

    res: list[NotificationLogPublic] = []
    for l in logs:
        recipient_name = l.recipient.full_name if l.recipient else None
        res.append(
            NotificationLogPublic(
                id=l.id,
                incident_id=l.incident_id,
                appointment_id=l.appointment_id,
                recipient_id=l.recipient_id,
                recipient_name=recipient_name,
                channel=l.channel,
                status=l.status,
                attempt_number=l.attempt_number,
                sent_at=l.sent_at,
                delivered_at=l.delivered_at,
                response_time_seconds=l.response_time_seconds,
                error_message=l.error_message,
                external_message_id=l.external_message_id,
                metadata_payload=l.metadata_payload,
                is_read=l.is_read,
                read_at=l.read_at,
            )
        )
    return res


@router.get("/my-notifications", response_model=InAppNotificationSummary, summary="Obtener bandeja de notificaciones in-app del usuario")
async def get_my_in_app_notifications(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Devuelve la lista de notificaciones recientes del usuario y el contador de no leídas."""
    repo = NotificationRepository(db)
    unread_count = await repo.count_unread_for_user(current_user.id)
    logs = await repo.list_by_recipient(current_user.id, limit=limit)

    items = [
        NotificationLogPublic(
            id=l.id,
            incident_id=l.incident_id,
            appointment_id=l.appointment_id,
            recipient_id=l.recipient_id,
            recipient_name=current_user.full_name,
            channel=l.channel,
            status=l.status,
            attempt_number=l.attempt_number,
            sent_at=l.sent_at,
            delivered_at=l.delivered_at,
            response_time_seconds=l.response_time_seconds,
            error_message=l.error_message,
            external_message_id=l.external_message_id,
            metadata_payload=l.metadata_payload,
            is_read=l.is_read,
            read_at=l.read_at,
        )
        for l in logs
    ]
    return InAppNotificationSummary(unread_count=unread_count, notifications=items)


@router.post("/{log_id}/read", response_model=NotificationLogPublic, summary="Marcar notificación como leída")
async def mark_notification_as_read(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marca una notificación específica como leída."""
    repo = NotificationRepository(db)
    log = await repo.get_by_id(log_id)
    if not log or log.recipient_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificación no encontrada.")
    updated = await repo.mark_as_read(log_id)
    await db.commit()
    return NotificationLogPublic.model_validate(updated)


@router.post("/mark-all-read", summary="Marcar todas las notificaciones como leídas")
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marca todas las notificaciones pendientes del usuario como leídas."""
    repo = NotificationRepository(db)
    count = await repo.mark_all_as_read_for_user(current_user.id)
    await db.commit()
    return {"marked_count": count}


@router.websocket("/ws")
async def notifications_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """Canal WebSocket para recepción de notificaciones In-App en tiempo real por usuario."""
    from app.core.security import decode_token
    from app.core.notification_hub import notification_hub

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await notification_hub.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        notification_hub.disconnect(user_id, websocket)
    except Exception:
        notification_hub.disconnect(user_id, websocket)

