"""Pruebas del servicio de notificaciones multicanal y cadena de fallback automático (plan/plan.md Módulo 6 y 2.B.7)."""

import datetime
import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService


@pytest.mark.anyio
async def test_notification_successful_primary_dispatch(client: AsyncClient):
    """Verifica el envío exitoso en el canal primario (WhatsApp) sin activar fallback."""
    async with AsyncSessionLocal() as db:
        service = NotificationService(db)
        repo = NotificationRepository(db)

        # Usuario paciente de prueba
        user = await db.get(User, "u3333333-3333-3333-3333-333333333333")
        assert user is not None
        user.preferred_notification_channels = ["WHATSAPP", "EMAIL"]
        await db.commit()

        # Despachar notificación
        logs = await service.send_multichannel_notification(
            recipient=user,
            subject="Cita Médica Confirmada",
            message="Su cita ha sido agendada con éxito.",
        )

        external_logs = [l for l in logs if l.channel != "IN_APP"]
        in_app_logs = [l for l in logs if l.channel == "IN_APP"]

        assert len(external_logs) == 1
        assert external_logs[0].channel == "WHATSAPP"
        assert external_logs[0].status == "SENT"
        assert external_logs[0].attempt_number == 1
        assert external_logs[0].external_message_id is not None
        assert external_logs[0].external_message_id.startswith("wamid.")

        # Verificar notificación In-App creada automáticamente
        assert len(in_app_logs) == 1
        assert in_app_logs[0].status == "DELIVERED"
        assert in_app_logs[0].is_read is False


@pytest.mark.anyio
async def test_notification_fallback_to_sms_when_whatsapp_fails(client: AsyncClient):
    """Simula una falla en WhatsApp y valida que el sistema active automáticamente el fallback a SMS/Voz (DoD Módulo 6)."""
    async with AsyncSessionLocal() as db:
        service = NotificationService(db)
        # Forzar falla en el proveedor de WhatsApp para activar fallback
        service.whatsapp._simulate_failure = True

        user = await db.get(User, "u3333333-3333-3333-3333-333333333333")
        assert user is not None
        user.preferred_notification_channels = ["WHATSAPP", "SMS"]
        await db.commit()

        logs = await service.send_multichannel_notification(
            recipient=user,
            subject="Aviso Urgente",
            message="Mensaje con tolerancia a fallos",
        )

        external_logs = [l for l in logs if l.channel != "IN_APP"]
        in_app_logs = [l for l in logs if l.channel == "IN_APP"]

        # Deben haberse generado 2 logs externos: Intento 1 (WHATSAPP fallido) e Intento 2 (SMS exitoso por fallback)
        assert len(external_logs) == 2

        # Intento 1: WhatsApp Fallido
        assert external_logs[0].channel == "WHATSAPP"
        assert external_logs[0].status == "FAILED"
        assert external_logs[0].attempt_number == 1
        assert external_logs[0].error_message is not None

        # Intento 2: Fallback automático a SMS
        assert external_logs[1].channel == "SMS"
        assert external_logs[1].status == "SENT"
        assert external_logs[1].attempt_number == 2
        assert external_logs[1].external_message_id is not None
        assert external_logs[1].external_message_id.startswith("SM")

        # Notificación In-App
        assert len(in_app_logs) == 1



@pytest.mark.anyio
async def test_user_notification_preferences_endpoints(client: AsyncClient):
    """Prueba la consulta y actualización de preferencias de canales de notificación vía API."""
    # Login Paciente
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Obtener preferencias actuales
    get_res = await client.get("/api/v1/notifications/my-preferences", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert "preferred_notification_channels" in data
    assert data["has_whatsapp"] is True

    # 2. Actualizar preferencias a WhatsApp + SMS
    put_res = await client.put(
        "/api/v1/notifications/my-preferences",
        json={"preferred_notification_channels": ["WHATSAPP", "SMS"]},
        headers=headers,
    )
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["preferred_notification_channels"] == ["WHATSAPP", "SMS"]

    # 3. Intentar lista vacía -> 400 Bad Request
    bad_res = await client.put(
        "/api/v1/notifications/my-preferences",
        json={"preferred_notification_channels": []},
        headers=headers,
    )
    assert bad_res.status_code == 400


@pytest.mark.anyio
async def test_in_app_notifications_center(client: AsyncClient):
    """Prueba la consulta de la bandeja In-App, conteo de no leídas y marcado como leídas."""
    # Login Paciente
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Obtener bandeja de notificaciones
    res = await client.get("/api/v1/notifications/my-notifications", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "unread_count" in data
    assert "notifications" in data
    assert isinstance(data["notifications"], list)

    if data["notifications"]:
        first_id = data["notifications"][0]["id"]
        # 2. Marcar una como leída
        read_res = await client.post(f"/api/v1/notifications/{first_id}/read", headers=headers)
        assert read_res.status_code == 200
        assert read_res.json()["is_read"] is True

    # 3. Marcar todas como leídas
    all_read = await client.post("/api/v1/notifications/mark-all-read", headers=headers)
    assert all_read.status_code == 200
    assert "marked_count" in all_read.json()

    # 4. Comprobar que el contador de no leídas quedó en 0
    fresh_res = await client.get("/api/v1/notifications/my-notifications", headers=headers)
    assert fresh_res.status_code == 200
    assert fresh_res.json()["unread_count"] == 0

