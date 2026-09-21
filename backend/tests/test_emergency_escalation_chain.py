"""Tests para Urgencias Médicas, Despacho SOS, Escalamiento Multicanal y Torre de Control (plan/plan.md 2.B.7)."""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_sos_trigger_requires_disclaimer(client: AsyncClient):
    # Login Paciente
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert pat_login.status_code == 200
    pat_token = pat_login.json()["access_token"]
    pat_headers = {"Authorization": f"Bearer {pat_token}"}

    # Intentar SOS sin descargo legal aceptado -> Debe rechazar con 400
    sos_payload = {
        "disclaimer_acknowledged": False,
        "chief_complaint": "Dolor abdominal agudo y sangrado",
        "latitude": 10.4806,
        "longitude": -66.9036,
        "address": "Av. Principal, Caracas",
    }
    resp = await client.post("/api/v1/emergencies/sos", json=sos_payload, headers=pat_headers)
    assert resp.status_code == 400
    assert "descargo legal" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_sos_dispatch_and_doctor_accept_and_resolve(client: AsyncClient):
    # 1. Login Paciente
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert pat_login.status_code == 200
    pat_token = pat_login.json()["access_token"]
    pat_headers = {"Authorization": f"Bearer {pat_token}"}

    # 2. Login Médico de Guardia (doctor@intimasalud.com - VERIFIED)
    doc_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "doctor@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_data = doc_login.json()
    doc_token = doc_data["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}
    doc_me = await client.get("/api/v1/auth/me", headers=doc_headers)
    doc_id = doc_me.json()["id"]

    # 3. Paciente dispara SOS con descargo aceptado
    sos_payload = {
        "disclaimer_acknowledged": True,
        "chief_complaint": "Contracciones intensas y fiebre repentina",
        "latitude": 10.4900,
        "longitude": -66.8900,
        "address": "Calle 4, Altamira",
    }
    sos_resp = await client.post("/api/v1/emergencies/sos", json=sos_payload, headers=pat_headers)
    assert sos_resp.status_code == 201
    incident = sos_resp.json()
    incident_id = incident["id"]
    assert incident["status"] in ("DISPATCHED", "ESCALATED_MODERATOR")
    assert incident["chief_complaint"] == "Contracciones intensas y fiebre repentina"

    # 4. Médico toma el caso SOS
    accept_resp = await client.post(f"/api/v1/emergencies/{incident_id}/accept", headers=doc_headers)
    assert accept_resp.status_code == 200
    accepted_data = accept_resp.json()
    assert accepted_data["status"] == "ACCEPTED"
    assert accepted_data["assigned_doctor_id"] == doc_id
    assert accepted_data["response_time_seconds"] is not None

    # 5. Médico resuelve el caso con notas de triaje
    resolve_payload = {
        "triage_notes": "Orientación gineco-obstétrica de urgencia efectuada. Se coordinó traslado en ambulancia."
    }
    resolve_resp = await client.post(
        f"/api/v1/emergencies/{incident_id}/resolve",
        json=resolve_payload,
        headers=doc_headers,
    )
    assert resolve_resp.status_code == 200
    resolved_data = resolve_resp.json()
    assert resolved_data["status"] == "RESOLVED"
    assert resolved_data["triage_notes"] == resolve_payload["triage_notes"]
    assert resolved_data["resolved_at"] is not None

    # 6. Paciente o Médico consulta la línea de auditoría
    audit_resp = await client.get(f"/api/v1/emergencies/{incident_id}/audit-timeline", headers=pat_headers)
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    assert len(logs) >= 2
    # Verificar que existan logs de despacho y de aceptación/resolución
    actions = [log["error_message"] for log in logs if log.get("error_message")]
    assert any("tomó el caso" in a or "despachada" in a for a in actions)
    assert any("cerrado y finalizado" in a for a in actions)


@pytest.mark.anyio
async def test_emergency_multichannel_escalation_chain(client: AsyncClient):
    # 1. Login Paciente y SuperAdmin
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}

    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    # 2. Paciente genera SOS
    sos_resp = await client.post(
        "/api/v1/emergencies/sos",
        json={
            "disclaimer_acknowledged": True,
            "chief_complaint": "Sospecha de preeclampsia, dolor de cabeza severo",
            "latitude": 10.50,
            "longitude": -66.91,
        },
        headers=pat_headers,
    )
    assert sos_resp.status_code == 201
    incident_id = sos_resp.json()["id"]

    # 3. Escalamiento paso a paso por SLA Timeout
    # Escalado 1 -> Doctor 2 o Torre de Control
    esc1_resp = await client.post(f"/api/v1/emergencies/{incident_id}/escalate", headers=admin_headers)
    assert esc1_resp.status_code == 200
    esc1_data = esc1_resp.json()
    assert esc1_data["escalation_level"] in (2, 3)

    # Si está en nivel 2, escalar a nivel 3 (Moderador)
    if esc1_data["escalation_level"] == 2:
        esc2_resp = await client.post(f"/api/v1/emergencies/{incident_id}/escalate", headers=admin_headers)
        assert esc2_resp.status_code == 200
        assert esc2_resp.json()["status"] == "ESCALATED_MODERATOR"
        assert esc2_resp.json()["escalation_level"] == 3

    # Escalado a nivel 4 (Línea de contingencia telefónica)
    esc_backup_resp = await client.post(f"/api/v1/emergencies/{incident_id}/escalate", headers=admin_headers)
    assert esc_backup_resp.status_code == 200
    backup_data = esc_backup_resp.json()
    assert backup_data["status"] == "ESCALATED_BACKUP"
    assert backup_data["escalation_level"] == 4

    # Verificar que el canal VOICE_CALL fue registrado en auditoría
    audit_resp = await client.get(f"/api/v1/emergencies/{incident_id}/audit-timeline", headers=admin_headers)
    assert audit_resp.status_code == 200
    channels = [log["channel"] for log in audit_resp.json()]
    assert "VOICE_CALL" in channels


@pytest.mark.anyio
async def test_control_tower_access_control(client: AsyncClient):
    # Paciente no tiene permiso de monitoreo de torre de control -> 403
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}
    forbidden_resp = await client.get("/api/v1/emergencies/active", headers=pat_headers)
    assert forbidden_resp.status_code == 403

    # SuperAdmin tiene permiso de monitoreo -> 200
    admin_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    admin_resp = await client.get("/api/v1/emergencies/active", headers=admin_headers)
    assert admin_resp.status_code == 200
    assert isinstance(admin_resp.json(), list)
