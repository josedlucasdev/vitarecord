"""Pruebas de los Webhooks de WhatsApp y Twilio con interactividad Aceptar/Rechazar (plan/plan.md Módulo 6 y 2.B.5)."""

import datetime
import random
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.notification_log import NotificationLog


@pytest.mark.anyio
async def test_whatsapp_webhook_verification(client: AsyncClient):
    """Verifica el handshake de suscripción exigido por Meta Graph API."""
    # 1. Con token correcto y hub.mode=subscribe -> 200 con challenge en texto plano
    challenge = "challenge_code_123456"
    res = await client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WHATSAPP_VERIFY_TOKEN,
            "hub.challenge": challenge,
        },
    )
    assert res.status_code == 200
    assert res.text == challenge

    # 2. Con token incorrecto -> 403 Forbidden
    bad_res = await client.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "token_invalido_hacker",
            "hub.challenge": challenge,
        },
    )
    assert bad_res.status_code == 403


@pytest.mark.anyio
async def test_whatsapp_delivery_receipt_callback(client: AsyncClient):
    """Verifica la recepción de confirmaciones de entrega de WhatsApp y actualización de notification_logs."""
    async with AsyncSessionLocal() as db:
        test_wamid = f"wamid.HBgM{random.randint(100000, 999999)}"
        log = NotificationLog(
            recipient_id="u3333333-3333-3333-3333-333333333333",
            channel="WHATSAPP",
            status="SENT",
            attempt_number=1,
            external_message_id=test_wamid,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        log_id = log.id

    # Simular callback de entrega de Meta
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "statuses": [
                                {
                                    "id": test_wamid,
                                    "status": "delivered",
                                    "timestamp": "1726000000",
                                    "recipient_id": "584141234567",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    res = await client.post("/api/v1/webhooks/whatsapp", json=payload)
    assert res.status_code == 200
    assert res.json() == {"status": "processed"}

    # Comprobar que en la base de datos se actualizó a DELIVERED
    async with AsyncSessionLocal() as db:
        updated_log = await db.get(NotificationLog, log_id)
        assert updated_log.status == "DELIVERED"
        assert updated_log.delivered_at is not None


@pytest.mark.anyio
async def test_whatsapp_interactive_accept_and_reject_flow(client: AsyncClient):
    """Prueba el ciclo de respuesta interactiva del paciente vía WhatsApp ([Aceptar] y [Rechazar])."""
    # 1. Login Recepción
    rec_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    rec_token = rec_login.json()["access_token"]
    rec_headers = {"Authorization": f"Bearer {rec_token}"}

    # 2. Login Paciente
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    pat_token = pat_login.json()["access_token"]
    pat_headers = {"Authorization": f"Bearer {pat_token}"}
    pat_me = await client.get("/api/v1/auth/me", headers=pat_headers)
    patient_id = pat_me.json()["id"]

    # 3. Crear primera cita propuesta (para ACEPTAR vía WhatsApp)
    delta1 = datetime.timedelta(days=random.randint(2000, 5000), hours=random.randint(8, 16))
    start_dt1 = datetime.datetime.now(datetime.timezone.utc) + delta1
    end_dt1 = start_dt1 + datetime.timedelta(minutes=30)
    app1_res = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": "c1111111-1111-1111-1111-111111111111",
            "doctor_id": "u2222222-2222-2222-2222-222222222222",
            "patient_id": patient_id,
            "room_id": "r1111111-1111-1111-1111-111111111111",
            "start_time": start_dt1.isoformat(),
            "end_time": end_dt1.isoformat(),
            "reason": "Cita para aceptar por WhatsApp",
            "estimated_amount": 35.00,
        },
        headers=rec_headers,
    )
    assert app1_res.status_code == 201
    app1_id = app1_res.json()["id"]
    assert app1_res.json()["status"] == "PENDING_PATIENT_ACCEPTANCE"


    # Enviar evento de botón [Aceptar] desde WhatsApp
    accept_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "584141234567",
                                    "type": "interactive",
                                    "interactive": {
                                        "button_reply": {
                                            "id": f"accept_appointment_{app1_id}",
                                            "title": "Aceptar Cita",
                                        }
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }
    wh_accept = await client.post("/api/v1/webhooks/whatsapp", json=accept_payload)
    assert wh_accept.status_code == 200

    # Verificar que la cita 1 ahora está CONFIRMED
    get_app1 = await client.get(f"/api/v1/appointments/{app1_id}", headers=rec_headers)
    assert get_app1.json()["status"] == "CONFIRMED"

    # 4. Crear segunda cita propuesta (para RECHAZAR vía WhatsApp)
    delta2 = datetime.timedelta(days=random.randint(5001, 8000), hours=random.randint(8, 16))
    start_dt2 = datetime.datetime.now(datetime.timezone.utc) + delta2
    end_dt2 = start_dt2 + datetime.timedelta(minutes=30)

    app2_res = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": "c1111111-1111-1111-1111-111111111111",
            "doctor_id": "u2222222-2222-2222-2222-222222222222",
            "patient_id": patient_id,
            "room_id": "r1111111-1111-1111-1111-111111111111",
            "start_time": start_dt2.isoformat(),
            "end_time": end_dt2.isoformat(),
            "reason": "Cita para rechazar por WhatsApp",
            "estimated_amount": 35.00,
        },
        headers=rec_headers,
    )
    assert app2_res.status_code == 201
    app2_id = app2_res.json()["id"]

    # Enviar evento de botón [Rechazar] desde WhatsApp
    reject_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "584141234567",
                                    "type": "interactive",
                                    "interactive": {
                                        "button_reply": {
                                            "id": f"reject_appointment_{app2_id}",
                                            "title": "Rechazar Cita",
                                        }
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }
    wh_reject = await client.post("/api/v1/webhooks/whatsapp", json=reject_payload)
    assert wh_reject.status_code == 200

    # Verificar que la cita 2 quedó en REJECTED_BY_PATIENT y el pago en EXEMPT
    get_app2 = await client.get(f"/api/v1/appointments/{app2_id}", headers=rec_headers)
    assert get_app2.json()["status"] == "REJECTED_BY_PATIENT"
    assert get_app2.json()["payment_status"] == "EXEMPT"


@pytest.mark.anyio
async def test_twilio_webhook_delivery_status(client: AsyncClient):
    """Verifica el callback de entrega de SMS/Voz de Twilio."""
    test_sid = f"SM{random.randint(100000, 999999)}"
    async with AsyncSessionLocal() as db:
        log = NotificationLog(
            recipient_id="u3333333-3333-3333-3333-333333333333",
            channel="SMS",
            status="SENT",
            attempt_number=1,
            external_message_id=test_sid,
        )
        db.add(log)
        await db.commit()
        log_id = log.id

    # Enviar callback de Twilio
    res = await client.post(
        "/api/v1/webhooks/twilio",
        data={"MessageSid": test_sid, "MessageStatus": "delivered"},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "received"}

    async with AsyncSessionLocal() as db:
        updated_log = await db.get(NotificationLog, log_id)
        assert updated_log.status == "DELIVERED"
        assert updated_log.delivered_at is not None
