import datetime
import random
from decimal import Decimal
import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.affiliation import DoctorClinicAffiliation
from app.models.procedure import MedicalProcedure
from sqlalchemy import select


@pytest.mark.anyio
async def test_doctor_independent_fee_and_procedures(client: AsyncClient):
    clinic_id = "c1111111-1111-1111-1111-111111111111"

    # 1. Login Médico (Dr. Alejandro Morales)
    doc_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "doctor@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert doc_login.status_code == 200
    doc_token = doc_login.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}
    doc_me = (await client.get("/api/v1/auth/me", headers=doc_headers)).json()
    doctor_id = doc_me["id"]

    # 2. Login Paciente
    pat_login = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert pat_login.status_code == 200
    pat_token = pat_login.json()["access_token"]
    pat_headers = {"Authorization": f"Bearer {pat_token}"}

    # A. El médico consulta sus afiliaciones y tarifas
    res_aff = await client.get("/api/v1/doctors/me/affiliations", headers=doc_headers)
    assert res_aff.status_code == 200
    affs = res_aff.json()
    assert len(affs) > 0
    my_aff = next(a for a in affs if a["clinic_id"] == clinic_id)
    assert my_aff["can_edit_fee"] is True  # INDEPENDENT

    # B. El médico actualiza su tarifa de consulta a $45.00
    res_update_fee = await client.put(
        f"/api/v1/doctors/me/affiliations/{clinic_id}/fee",
        headers=doc_headers,
        json={"consultation_fee": 45.00, "currency": "USD"},
    )
    assert res_update_fee.status_code == 200
    assert float(res_update_fee.json()["consultation_fee"]) == 45.00

    # C. El médico crea un procedimiento personalizado propio
    proc_name = f"Procedimiento Test Dr {random.randint(1000, 9999)}"
    res_proc = await client.post(
        f"/api/v1/clinics/{clinic_id}/procedures",
        headers=doc_headers,
        json={
            "name": proc_name,
            "description": "Procedimiento de prueba",
            "price": 35.00,
            "currency": "USD",
            "duration_minutes": 20,
            "category": "Especializado",
        },
    )
    assert res_proc.status_code == 201
    custom_proc = res_proc.json()
    custom_proc_id = custom_proc["id"]
    assert custom_proc["name"] == proc_name
    assert float(custom_proc["price"]) == 35.00

    # D. Consulta del catálogo para este médico
    res_cat = await client.get(f"/api/v1/clinics/{clinic_id}/procedures?doctor_id={doctor_id}")
    assert res_cat.status_code == 200
    catalog = res_cat.json()
    assert any(p["id"] == custom_proc_id for p in catalog)

    # E. El paciente agenda una cita seleccionando el procedimiento personalizado
    day_offset = random.randint(1000, 5000)
    future_date = datetime.date.today() + datetime.timedelta(days=day_offset)
    start_dt = datetime.datetime.combine(future_date, datetime.time(10, 0))
    end_dt = datetime.datetime.combine(future_date, datetime.time(10, 30))

    res_book = await client.post(
        "/api/v1/appointments",
        headers=pat_headers,
        json={
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "procedure_ids": [custom_proc_id],
            "reason": "Consulta con procedimiento personalizado",
        },
    )
    assert res_book.status_code in (200, 201)
    app_data = res_book.json()

    # Total en caja debe ser consulta ($45) + procedimiento ($35) = $80
    assert float(app_data["payment_amount"]) == 80.00
    assert float(app_data["consultation_fee"]) == 45.00
    assert len(app_data["procedures"]) == 1
    assert app_data["procedures"][0]["id"] is not None

    # F. Durante la consulta, el médico agrega un procedimiento adicional realizado ($20.00)
    app_id = app_data["id"]
    res_add_proc = await client.post(
        f"/api/v1/appointments/{app_id}/procedures",
        headers=doc_headers,
        json={
            "name": "Procedimiento Adicional en Consulta",
            "price": 20.00,
            "currency": "USD",
            "notes": "Realizado intra-consulta",
        },
    )
    assert res_add_proc.status_code == 200
    updated_app = res_add_proc.json()
    # Total en caja ahora debe ser 80 + 20 = $100
    assert float(updated_app["payment_amount"]) == 100.00
    assert len(updated_app["procedures"]) == 2
