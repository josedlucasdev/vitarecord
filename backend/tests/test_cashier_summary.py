import datetime
from decimal import Decimal
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_manual_payment_collection_and_daily_cashier_summary(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"

    # 1. Login Recepción
    rec_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    rec_token = rec_login.json()["access_token"]
    rec_headers = {"Authorization": f"Bearer {rec_token}"}

    # 2. Login Paciente y obtener ID
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    pat_token = pat_login.json()["access_token"]
    pat_headers = {"Authorization": f"Bearer {pat_token}"}
    pat_me = await client.get("/api/v1/auth/me", headers=pat_headers)
    patient_id = pat_me.json()["id"]

    # 3. Paciente agenda cita con fecha dinámica
    import random
    today = datetime.date.today() + datetime.timedelta(days=random.randint(500, 10000))
    start_dt = datetime.datetime.combine(today, datetime.time(14, 0))
    end_dt = datetime.datetime.combine(today, datetime.time(14, 30))

    book_resp = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "reason": "Consulta con cobro en efectivo",
            "estimated_amount": 50.00,
        },
        headers=pat_headers,
    )
    assert book_resp.status_code == 201
    app_id = book_resp.json()["id"]

    # 4. Recepción registra el cobro en efectivo
    pay_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/payments/{app_id}/record",
        json={
            "amount": 50.00,
            "payment_method": "CASH",
            "reference": "REC-00123",
            "notes": "Pago exacto en billetes",
        },
        headers=rec_headers,
    )
    assert pay_resp.status_code == 200
    pay_data = pay_resp.json()
    assert pay_data["status"] == "PAID"
    assert pay_data["payment_method"] == "CASH"
    assert Decimal(str(pay_data["amount"])) == Decimal("50.00")

    # 5. Consultar cuadre diario de caja (tanto por fecha de pago de hoy como por fecha de cita)
    summary_resp = await client.get(
        f"/api/v1/clinics/{clinic_id}/cashier/daily-summary?date={today.isoformat()}",
        headers=rec_headers,
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert Decimal(str(summary["total_collected"])) >= Decimal("50.00")
    assert Decimal(str(summary["by_method"]["CASH"])) >= Decimal("50.00")
    assert summary["paid_count"] >= 1

    # Verificar que el arqueo de HOY también refleja el cobro recibido hoy
    from app.core.timezones import today_in
    today_real = today_in("America/Caracas").isoformat()
    today_resp = await client.get(
        f"/api/v1/clinics/{clinic_id}/cashier/daily-summary?date={today_real}",
        headers=rec_headers,
    )
    assert today_resp.status_code == 200
    today_summary = today_resp.json()
    assert Decimal(str(today_summary["total_collected"])) >= Decimal("50.00")
    assert Decimal(str(today_summary["by_method"]["CASH"])) >= Decimal("50.00")
    assert today_summary["paid_count"] >= 1


@pytest.mark.anyio
async def test_record_payment_creates_payment_record_if_missing(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"
    doctor_id = "u2222222-2222-2222-2222-222222222222"

    rec_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    rec_headers = {"Authorization": f"Bearer {rec_login.json()['access_token']}"}

    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    pat_headers = {"Authorization": f"Bearer {pat_login.json()['access_token']}"}

    import random
    future_date = datetime.date.today() + datetime.timedelta(days=random.randint(1000, 20000))
    start_dt = datetime.datetime.combine(future_date, datetime.time(10, 0))
    end_dt = datetime.datetime.combine(future_date, datetime.time(10, 30))

    book_resp = await client.post(
        "/api/v1/appointments",
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "reason": "Consulta sin registro contable previo",
            "estimated_amount": 40.00,
        },
        headers=pat_headers,
    )
    assert book_resp.status_code == 201
    app_id = book_resp.json()["id"]

    # Simular eliminación del registro contable para recrear el escenario donde no existía
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        await session.execute(text("DELETE FROM payment_records WHERE appointment_id = :aid"), {"aid": app_id})
        await session.commit()

    # Recepción registra el cobro en taquilla: debe crearlo automáticamente y registrarlo como PAID
    pay_resp = await client.post(
        f"/api/v1/clinics/{clinic_id}/payments/{app_id}/record",
        json={
            "amount": 40.00,
            "payment_method": "PAGO_MOVIL",
            "reference": "PM-99201",
            "notes": "Cobro exitoso auto-creando registro contable",
        },
        headers=rec_headers,
    )
    assert pay_resp.status_code == 200
    data = pay_resp.json()
    assert data["status"] == "PAID"
    assert data["payment_method"] == "PAGO_MOVIL"
    assert Decimal(str(data["amount"])) == Decimal("40.00")


@pytest.mark.anyio
async def test_export_accounting_excel_endpoint(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    rec_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    rec_headers = {"Authorization": f"Bearer {rec_login.json()['access_token']}"}

    resp = await client.get(
        f"/api/v1/clinics/{clinic_id}/cashier/export-accounting-excel?bcv_rate=65.50",
        headers=rec_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "Libro_Contable_" in resp.headers["content-disposition"]
    assert len(resp.content) > 1000  # Archivo binario Excel válido con contenido
