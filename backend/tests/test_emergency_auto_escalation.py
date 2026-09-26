"""Orquestador AUTOMATICO de escalamiento de urgencias (plan/plan.md 2.B.7, Modulo 4 DoD).

Simula el paso del tiempo inyectando `now` en process_emergency_escalations():
- 15 s sin confirmacion de entrega -> llamada de voz de refuerzo al medico 1.
- 60 s sin aceptacion -> medico 2.
- 60 s sin aceptacion del ultimo medico -> moderador (llamada + alarma).
- 2 min sin reconocimiento del moderador -> linea de respaldo (VOICE_CALL).
- El reconocimiento del moderador detiene el paso a la linea de respaldo.
- Dos medicos que aceptan a la vez: solo uno se queda con el caso.
- El WebSocket de la Torre de Control rechaza conexiones sin token.
"""

import asyncio
import datetime

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.main import app
from app.repositories.emergency_repository import EmergencyRepository
from app.services.emergency_service import process_emergency_escalations

FORM = {"content-type": "application/x-www-form-urlencoded"}
CLINIC_1 = "c1111111-1111-1111-1111-111111111111"


async def _headers(client: AsyncClient, email: str) -> dict:
    resp = await client.post("/api/v1/auth/login", data={"username": email, "password": "Password123!"}, headers=FORM)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _trigger(client: AsyncClient) -> str:
    headers = await _headers(client, "paciente@intimasalud.com")
    resp = await client.post(
        "/api/v1/emergencies/sos",
        json={"disclaimer_acknowledged": True, "chief_complaint": "Sangrado abundante en embarazo", "clinic_id": CLINIC_1},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _load(incident_id: str):
    async with AsyncSessionLocal() as session:
        return await EmergencyRepository(session).get_by_id(incident_id)


def _since(incident) -> datetime.datetime:
    ts = incident.last_escalated_at or incident.triggered_at
    return ts if ts.tzinfo else ts.replace(tzinfo=datetime.timezone.utc)


@pytest.mark.anyio
async def test_automatic_escalation_chain_reaches_backup_line(client: AsyncClient):
    incident_id = await _trigger(client)
    incident = await _load(incident_id)
    if incident.status != "DISPATCHED":
        pytest.skip("La semilla no tiene medicos de guardia en la clinica 1")
    assert incident.escalation_level == 1

    # 1. 16 s sin confirmacion de entrega -> refuerzo por voz al mismo medico.
    await process_emergency_escalations(
        now=_since(incident) + datetime.timedelta(seconds=settings.EMERGENCY_DELIVERY_CONFIRM_SECONDS + 1)
    )
    incident = await _load(incident_id)
    assert incident.escalation_level == 1
    voice_lvl1 = [l for l in incident.notification_logs if l.channel == "VOICE_CALL" and l.attempt_number == 1]
    assert voice_lvl1 and voice_lvl1[0].recipient_id is not None

    # El refuerzo es idempotente: otro ciclo no vuelve a llamar.
    await process_emergency_escalations(
        now=_since(incident) + datetime.timedelta(seconds=settings.EMERGENCY_DELIVERY_CONFIRM_SECONDS + 5)
    )
    incident = await _load(incident_id)
    assert len([l for l in incident.notification_logs if l.channel == "VOICE_CALL" and l.attempt_number == 1]) == 1

    # 2. 60 s sin aceptar -> siguiente medico (o moderador si no hay mas).
    first_doctor = voice_lvl1[0].recipient_id
    await process_emergency_escalations(
        now=_since(incident) + datetime.timedelta(seconds=settings.EMERGENCY_DOCTOR_ACCEPT_TIMEOUT_SECONDS + 1)
    )
    incident = await _load(incident_id)
    assert incident.escalation_level == 2 or incident.status == "ESCALATED_MODERATOR"
    if incident.escalation_level == 2:
        assert incident.status == "ESCALATED_DOCTOR_2"
        second_doctors = {
            l.recipient_id for l in incident.notification_logs
            if l.attempt_number == 2 and l.channel in ("PUSH", "WHATSAPP")
        }
        assert second_doctors and first_doctor not in second_doctors

        # 3. 60 s mas -> moderador de turno.
        await process_emergency_escalations(
            now=_since(incident) + datetime.timedelta(seconds=settings.EMERGENCY_DOCTOR_ACCEPT_TIMEOUT_SECONDS + 1)
        )
        incident = await _load(incident_id)
    assert incident.status == "ESCALATED_MODERATOR"
    assert incident.escalation_level == 3

    # 4. Moderador sin reconocer en 2 min -> linea de respaldo.
    await process_emergency_escalations(
        now=_since(incident) + datetime.timedelta(seconds=settings.EMERGENCY_MODERATOR_SLA_SECONDS + 1)
    )
    incident = await _load(incident_id)
    assert incident.status == "ESCALATED_BACKUP"
    assert incident.escalation_level == 4
    assert any(l.channel == "VOICE_CALL" and l.attempt_number == 4 for l in incident.notification_logs)


@pytest.mark.anyio
async def test_moderator_acknowledge_stops_backup_escalation(client: AsyncClient):
    admin = await _headers(client, "admin@vitarecord.com")
    incident_id = await _trigger(client)

    # Llevar el incidente hasta el moderador con escalamientos manuales.
    for _ in range(5):
        incident = await _load(incident_id)
        if incident.status == "ESCALATED_MODERATOR":
            break
        resp = await client.post(f"/api/v1/emergencies/{incident_id}/escalate", headers=admin)
        assert resp.status_code == 200
    incident = await _load(incident_id)
    assert incident.status == "ESCALATED_MODERATOR"

    ack = await client.post(f"/api/v1/emergencies/{incident_id}/acknowledge", headers=admin)
    assert ack.status_code == 200
    assert ack.json()["acknowledged_at"] is not None

    await process_emergency_escalations(
        now=_since(incident) + datetime.timedelta(seconds=settings.EMERGENCY_MODERATOR_SLA_SECONDS * 3)
    )
    incident = await _load(incident_id)
    assert incident.status == "ESCALATED_MODERATOR"


@pytest.mark.anyio
async def test_only_one_doctor_can_take_the_case(client: AsyncClient):
    incident_id = await _trigger(client)
    doc_a = await _headers(client, "doctor@intimasalud.com")
    doc_b = await _headers(client, "dra.castillo@intimasalud.com")

    results = await asyncio.gather(
        client.post(f"/api/v1/emergencies/{incident_id}/accept", headers=doc_a),
        client.post(f"/api/v1/emergencies/{incident_id}/accept", headers=doc_b),
    )
    codes = sorted(r.status_code for r in results)
    assert codes == [200, 400]


@pytest.mark.anyio
async def test_only_assigned_doctor_can_resolve(client: AsyncClient):
    incident_id = await _trigger(client)
    doc_a = await _headers(client, "doctor@intimasalud.com")
    doc_b = await _headers(client, "dra.castillo@intimasalud.com")
    assert (await client.post(f"/api/v1/emergencies/{incident_id}/accept", headers=doc_a)).status_code == 200

    other = await client.post(
        f"/api/v1/emergencies/{incident_id}/resolve", json={"triage_notes": "Intento de otro medico"}, headers=doc_b
    )
    assert other.status_code == 403
    own = await client.post(
        f"/api/v1/emergencies/{incident_id}/resolve", json={"triage_notes": "Orientacion remota realizada"}, headers=doc_a
    )
    assert own.status_code == 200


def test_control_tower_websocket_requires_token():
    # Sin "with": no se ejecuta el lifespan (semilla y tareas periodicas).
    ws_client = TestClient(app)
    for url in ("/api/v1/emergencies/ws/control-tower", "/api/v1/emergencies/ws/control-tower?token=invalido"):
        with pytest.raises(WebSocketDisconnect):
            with ws_client.websocket_connect(url) as ws:
                ws.receive_text()
