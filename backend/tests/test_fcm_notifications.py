import uuid
import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.models.user import User
from app.repositories.device_token_repository import DeviceTokenRepository
from app.services.notification_service import NotificationService


@pytest.mark.anyio
async def test_register_and_list_fcm_device(client: AsyncClient):
    """Verifica el registro y consulta de tokens FCM de dispositivos vía API."""
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    fcm_sample_token = f"fcm_token_device_{uuid.uuid4().hex}"

    # 1. Registrar dispositivo
    resp = await client.post(
        "/api/v1/notifications/devices",
        headers=auth_headers,
        json={
            "fcm_token": fcm_sample_token,
            "platform": "android",
            "device_name": "Samsung Galaxy S23",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["fcm_token"] == fcm_sample_token
    assert data["platform"] == "android"
    assert data["device_name"] == "Samsung Galaxy S23"
    assert data["is_active"] is True
    device_id = data["id"]

    # 2. Listar dispositivos registrados
    list_resp = await client.get("/api/v1/notifications/devices", headers=auth_headers)
    assert list_resp.status_code == 200
    devices = list_resp.json()
    assert len(devices) >= 1
    assert any(d["fcm_token"] == fcm_sample_token for d in devices)

    # 3. Desvincular dispositivo
    del_resp = await client.delete(f"/api/v1/notifications/devices/{device_id}", headers=auth_headers)
    assert del_resp.status_code == 200

    # 4. Verificar que ya no está en la lista
    list_resp_after = await client.get("/api/v1/notifications/devices", headers=auth_headers)
    assert list_resp_after.status_code == 200
    assert not any(d["id"] == device_id for d in list_resp_after.json())


@pytest.mark.anyio
async def test_fcm_push_notification_dispatch(client: AsyncClient):
    """Verifica que NotificationService despache la notificación push vía FCM a los tokens registrados."""
    async with AsyncSessionLocal() as db:
        user = await db.get(User, "u3333333-3333-3333-3333-333333333333")
        assert user is not None
        user.preferred_notification_channels = ["PUSH", "WHATSAPP", "EMAIL"]
        await db.commit()

        repo = DeviceTokenRepository(db)
        fcm_token = f"fcm_test_push_token_{uuid.uuid4().hex}"
        await repo.register_device_token(
            user_id=user.id,
            fcm_token=fcm_token,
            platform="android",
            device_name="Google Pixel 8",
        )
        await db.commit()

        service = NotificationService(db)
        logs = await service.send_multichannel_notification(
            recipient=user,
            subject="Recordatorio de Consulta",
            message="Su cita médica está programada para mañana.",
            metadata_payload={"type": "APPOINTMENT_REMINDER"},
        )

        push_logs = [log for log in logs if log.channel == "PUSH"]
        assert len(push_logs) == 1
        assert push_logs[0].status == "SENT"
        assert push_logs[0].external_message_id is not None
        assert "fcm_projects_" in push_logs[0].external_message_id


@pytest.mark.anyio
async def test_fcm_push_failure_triggers_fallback_to_whatsapp(client: AsyncClient):
    """Verifica que si FCM Push falla, el sistema activa automáticamente el fallback hacia WhatsApp."""
    async with AsyncSessionLocal() as db:
        user = await db.get(User, "u3333333-3333-3333-3333-333333333333")
        assert user is not None
        user.preferred_notification_channels = ["PUSH", "WHATSAPP", "EMAIL"]
        await db.commit()

        repo = DeviceTokenRepository(db)
        fcm_token = f"fcm_fail_token_{uuid.uuid4().hex}"
        await repo.register_device_token(
            user_id=user.id,
            fcm_token=fcm_token,
            platform="ios",
            device_name="iPhone 15 Pro",
        )
        await db.commit()

        service = NotificationService(db)
        # Simular fallo en Firebase Cloud Messaging
        service.fcm._simulate_failure = True

        logs = await service.send_multichannel_notification(
            recipient=user,
            subject="Alerta Médica",
            message="Notificación con respaldo multicanal.",
        )

        # Debe haber un log fallido de PUSH
        failed_push = [log for log in logs if log.channel == "PUSH" and log.status == "FAILED"]
        assert len(failed_push) == 1
        assert "FCM Error" in (failed_push[0].error_message or "")

        # Y debe haber activado el fallback a WHATSAPP entregado con éxito
        successful_whatsapp = [log for log in logs if log.channel == "WHATSAPP" and log.status == "SENT"]
        assert len(successful_whatsapp) == 1
        assert successful_whatsapp[0].attempt_number == 2
