import uuid
import pytest
from httpx import AsyncClient, Response
from unittest.mock import patch, MagicMock


@pytest.mark.anyio
async def test_superadmin_can_configure_clinic_ai_settings(client: AsyncClient):
    """Verifica que el SuperAdmin puede activar y configurar la URL y API Key de IA por clínica sin exponer el token en claro."""
    from app.core.security import create_access_token
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic

    admin_token = create_access_token(
        "u1111111-1111-1111-1111-111111111111",
        role="SUPERADMIN",
        email="admin@vitarecord.com",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear clínica de prueba
    slug = f"clinica-ai-test-{uuid.uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica Especializada con IA",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    clinic_data = create_resp.json()
    clinic_id = clinic_data["id"]

    try:
        # Inicialmente la IA está inactiva
        assert clinic_data.get("ai_enabled") is False
        assert clinic_data.get("has_ai_key") is False

        # 2. Configurar IA para la clínica con modelo específico y activación de consulta asistida
        ai_resp = await client.put(
            f"/api/v1/clinics/{clinic_id}/ai-settings",
            json={
                "ai_enabled": True,
                "ai_api_url": "https://api.openai.com/v1/chat/completions",
                "ai_api_key": "sk-proj-secret-key-test-123456",
                "ai_model": "gpt-4o",
                "ai_consultation_assistant_enabled": True,
            },
            headers=admin_headers,
        )
        assert ai_resp.status_code == 200
        ai_data = ai_resp.json()
        assert ai_data["ai_enabled"] is True
        assert ai_data["ai_api_url"] == "https://api.openai.com/v1/chat/completions"
        assert ai_data["has_ai_key"] is True
        assert ai_data["ai_model"] == "gpt-4o"
        assert ai_data["ai_consultation_assistant_enabled"] is True
        # El token no debe ser expuesto en el JSON público
        assert "ai_api_key" not in ai_data or ai_data["ai_api_key"] is None

        # 3. Actualizar sin reenviar el token (mantener el token existente)
        ai_update_resp = await client.put(
            f"/api/v1/clinics/{clinic_id}/ai-settings",
            json={
                "ai_enabled": True,
                "ai_api_url": "https://custom-ai-gateway.local/v1/chat/completions",
                "ai_api_key": None,
                "ai_model": "claude-3-5-sonnet-20240620",
            },
            headers=admin_headers,
        )
        assert ai_update_resp.status_code == 200
        updated_data = ai_update_resp.json()
        assert updated_data["ai_api_url"] == "https://custom-ai-gateway.local/v1/chat/completions"
        assert updated_data["has_ai_key"] is True
        assert updated_data["ai_model"] == "claude-3-5-sonnet-20240620"

    finally:
        async with AsyncSessionLocal() as db:
            c_obj = await db.get(Clinic, clinic_id)
            if c_obj:
                await db.delete(c_obj)
                await db.commit()


@pytest.mark.anyio
async def test_non_admin_cannot_configure_clinic_ai_settings(client: AsyncClient):
    """Verifica que un usuario no autorizado no puede modificar la configuración de IA de la clínica."""
    from app.core.security import create_access_token

    patient_token = create_access_token(
        "u2222222-2222-2222-2222-222222222222",
        role="PATIENT",
        email="paciente@vitarecord.com",
    )
    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    resp = await client.put(
        "/api/v1/clinics/c1111111-1111-1111-1111-111111111111/ai-settings",
        json={
            "ai_enabled": True,
            "ai_api_url": "https://malicious-url.com",
            "ai_api_key": "bad-key",
        },
        headers=patient_headers,
    )
    assert resp.status_code == 403


@pytest.mark.anyio
async def test_doctor_ai_assist_rejected_when_ai_disabled(client: AsyncClient):
    """Verifica que la asistencia de IA es rechazada si la clínica no tiene la IA habilitada."""
    from app.core.security import create_access_token
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic

    admin_token = create_access_token(
        "u1111111-1111-1111-1111-111111111111",
        role="SUPERADMIN",
        email="admin@vitarecord.com",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Crear clínica con IA desactivada
    slug = f"clinica-no-ai-{uuid.uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica Sin IA",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
            "ai_enabled": False,
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    clinic_id = create_resp.json()["id"]

    try:
        doctor_token = create_access_token(
            "u2222222-2222-2222-2222-222222222222",
            role="DOCTOR",
            clinic_id=clinic_id,
            email="doctor@vitarecord.com",
        )
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}

        assist_resp = await client.post(
            "/api/v1/medical-records/ai-assist",
            json={
                "clinic_id": clinic_id,
                "field_type": "anamnesis",
                "text": "Paciente con dolor de cabeza continuo desde hace 3 dias.",
            },
            headers=doctor_headers,
        )
        assert assist_resp.status_code == 403
        assert "no está activo para esta sede" in assist_resp.json()["detail"]
    finally:
        async with AsyncSessionLocal() as db:
            c_obj = await db.get(Clinic, clinic_id)
            if c_obj:
                await db.delete(c_obj)
                await db.commit()


@pytest.mark.anyio
async def test_doctor_ai_assist_success_with_mocked_gateway(client: AsyncClient):
    """Verifica que el médico tratante puede invocar el asistente de IA y recibir la propuesta redactada."""
    from app.core.security import create_access_token
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic
    from unittest.mock import AsyncMock

    admin_token = create_access_token(
        "u1111111-1111-1111-1111-111111111111",
        role="SUPERADMIN",
        email="admin@vitarecord.com",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    slug = f"clinica-ai-active-{uuid.uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica Activa con IA",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
            "ai_enabled": True,
            "ai_api_url": "https://api.openai.com/v1/chat/completions",
            "ai_api_key": "sk-proj-mock-key-for-test",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    clinic_id = create_resp.json()["id"]

    try:
        doctor_token = create_access_token(
            "u2222222-2222-2222-2222-222222222222",
            role="DOCTOR",
            clinic_id=clinic_id,
            email="doctor@vitarecord.com",
        )
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Paciente femenina de 28 años que refiere cuadro clínico de 72 horas de evolución caracterizado por cefalea holocraneal de intensidad moderada."
                    }
                }
            ],
            "usage": {"total_tokens": 92},
        }

        import httpx

        orig_post = httpx.AsyncClient.post

        async def mocked_post(self, url, *args, **kwargs):
            if "api.openai.com" in str(url):
                return mock_response
            return await orig_post(self, url, *args, **kwargs)

        with patch.object(httpx.AsyncClient, "post", new=mocked_post):
            assist_resp = await client.post(
                "/api/v1/medical-records/ai-assist",
                json={
                    "clinic_id": clinic_id,
                    "field_type": "anamnesis",
                    "text": "paciente femenina de 28 anos viene por dolor de cabeza desde hace 3 dias",
                },
                headers=doctor_headers,
            )

            assert assist_resp.status_code == 200
            data = assist_resp.json()
            assert "cefalea holocraneal" in data["enhanced_text"]
            assert data["tokens_used"] == 92
            assert data["provider"] == "external_ai_gateway"

    finally:
        async with AsyncSessionLocal() as db:
            c_obj = await db.get(Clinic, clinic_id)
            if c_obj:
                await db.delete(c_obj)
                await db.commit()


@pytest.mark.anyio
async def test_superadmin_can_query_ai_models(client: AsyncClient):
    """Verifica que el superadmin puede consultar los modelos disponibles de un proveedor de IA."""
    from app.core.security import create_access_token

    admin_token = create_access_token(
        "u1111111-1111-1111-1111-111111111111",
        role="SUPERADMIN",
        email="admin@vitarecord.com",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    mock_models_response = MagicMock()
    mock_models_response.status_code = 200
    mock_models_response.json.return_value = {
        "data": [
            {"id": "gpt-4o", "created": 1715368132},
            {"id": "gpt-4o-mini", "created": 1721172741},
            {"id": "o1-preview", "created": 1726090400},
            {"id": "text-embedding-3-small", "created": 1705948997},
            {"id": "dall-e-3", "created": 1698785189},
        ]
    }

    import httpx

    orig_get = httpx.AsyncClient.get

    async def mocked_get(self, url, *args, **kwargs):
        if "api.openai.com" in str(url):
            return mock_models_response
        return await orig_get(self, url, *args, **kwargs)

    with patch.object(httpx.AsyncClient, "get", new=mocked_get):
        resp = await client.post(
            "/api/v1/clinics/query-ai-models",
            json={
                "ai_api_url": "https://api.openai.com/v1/chat/completions",
                "ai_api_key": "sk-mock-key-for-listing",
            },
            headers=admin_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "gpt-4o-mini" in data["models"]
        assert "gpt-4o" in data["models"]
        assert "o1-preview" in data["models"]
        # Audio, embeddings and image models should have been filtered out
        assert "dall-e-3" not in data["models"]
        assert "text-embedding-3-small" not in data["models"]


@pytest.mark.anyio
async def test_ai_consultation_assist_full_flow(client: AsyncClient):
    """Verifica el flujo completo de consulta asistida por IA: grabación/anexos, análisis de IA y prellenado."""
    from app.core.security import create_access_token
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic
    from app.models.appointment import Appointment
    from app.models.user import User
    from app.models.medical_attachment import MedicalAttachment
    from sqlalchemy import select
    import datetime
    import json


    admin_token = create_access_token(
        "u1111111-1111-1111-1111-111111111111",
        role="SUPERADMIN",
        email="admin@vitarecord.com",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Crear clínica con IA habilitada
    slug = f"clinica-ai-flow-{uuid.uuid4().hex[:6]}"
    create_clinic_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica Asistencia IA",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
            "ai_enabled": True,
            "ai_api_url": "https://api.openai.com/v1/chat/completions",
            "ai_api_key": "sk-mock-key-for-test",
            "ai_model": "gpt-4o",
            "ai_consultation_assistant_enabled": True,
        },
        headers=admin_headers,
    )
    assert create_clinic_resp.status_code == 201
    clinic_id = create_clinic_resp.json()["id"]

    doctor_id = str(uuid.uuid4())
    patient_id = str(uuid.uuid4())
    appointment_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        # Crear doctor con especialidad
        doc_user = User(
            id=doctor_id,
            email=f"doc-{uuid.uuid4().hex[:6]}@vitarecord.com",
            full_name="Dra. Andrea Briceño",
            role="DOCTOR",
            specialty="Ginecología y Obstetricia",
            hashed_password="hash",
            status="ACTIVE",
            license_verification_status="VERIFIED",
        )
        # Crear paciente
        pat_user = User(
            id=patient_id,
            email=f"pat-{uuid.uuid4().hex[:6]}@vitarecord.com",
            full_name="Carla Mendoza",
            role="PATIENT",
            hashed_password="hash",
            status="ACTIVE",
        )


        # Crear cita
        now = datetime.datetime.now(datetime.timezone.utc)
        appt = Appointment(
            id=appointment_id,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            start_time=now,
            end_time=now + datetime.timedelta(minutes=30),
            status="IN_CONSULTATION",
            reason="Dolor pélvico agudo y dismenorrea",
        )
        db.add_all([doc_user, pat_user, appt])
        await db.commit()

    try:
        doctor_token = create_access_token(
            doctor_id,
            role="DOCTOR",
            clinic_id=clinic_id,
            email=doc_user.email,
        )
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}

        # 2. Subir audio grabado a la cita
        audio_content = b"fake-audio-bytes-of-recorded-consultation"
        files = {
            "file": ("consulta_audio.webm", audio_content, "audio/webm"),
        }
        data = {"attachment_type": "CONSULTATION_AUDIO"}
        upload_resp = await client.post(
            f"/api/v1/appointments/{appointment_id}/attachments",
            files=files,
            data=data,
            headers=doctor_headers,
        )
        assert upload_resp.status_code == 201
        upload_data = upload_resp.json()
        assert upload_data["attachment_type"] == "CONSULTATION_AUDIO"
        assert upload_data["appointment_id"] == appointment_id
        audio_attachment_id = upload_data["id"]

        # 3. Invocar AI Consultation Assist con mock
        mock_ai_json = {
            "anamnesis": "Paciente femenina de 32 años que refiere dolor pélvico cíclico de moderada a fuerte intensidad de 6 meses de evolución.",
            "physical_exam": "Abdomen blando, depresible, con dolor a la palpación profunda en fosa ilíaca izquierda. Tacto bimanual doloroso.",
            "diagnosis": "Dismenorrea secundaria / sospecha de endometriosis ovárica izquierda.",
            "icd10_code": "N80.1",
            "icd10_description": "Endometriosis del ovario",
            "plan": "Se solicita ecografía transvaginal de alta resolución con mapeo de endometriosis. Tratamiento analgésico y hormonal.",
            "prescriptions": [
                {
                    "medication": "Ibuprofeno",
                    "dosage": "600 mg",
                    "frequency": "Cada 8 horas",
                    "duration": "5 días",
                    "instructions": "Vía oral con alimentos",
                }
            ],
            "clinical_summary": "Caso compatible con dismenorrea por endometriosis ovárica. Se programa ecografía diagnóstica.",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(mock_ai_json)
                    }
                }
            ],
            "usage": {"total_tokens": 320},
        }

        import httpx

        orig_post = httpx.AsyncClient.post

        async def mocked_post(self, url, *args, **kwargs):
            if "api.openai.com" in str(url):
                return mock_response
            return await orig_post(self, url, *args, **kwargs)

        with patch.object(httpx.AsyncClient, "post", new=mocked_post):
            assist_resp = await client.post(
                "/api/v1/medical-records/ai-consultation-assist",
                json={
                    "appointment_id": appointment_id,
                    "transcript": "Doctor: Cuénteme qué molestia siente. Paciente: Tengo un dolor muy fuerte en el vientre desde hace 6 meses que empeora con mi ciclo.",
                    "doctor_specialty": "Ginecología y Obstetricia",
                },
                headers=doctor_headers,
            )
            assert assist_resp.status_code == 200
            res_data = assist_resp.json()
            assert res_data["icd10_code"] == "N80.1"
            assert "endometriosis" in res_data["diagnosis"].lower()
            assert len(res_data["prescriptions"]) == 1
            assert res_data["prescriptions"][0]["medication"] == "Ibuprofeno"

        # 4. Finalizar consulta y verificar vinculación de adjuntos a la historia médica
        finish_resp = await client.post(
            "/api/v1/medical-records",
            json={
                "appointment_id": appointment_id,
                "anamnesis": res_data["anamnesis"],
                "physical_exam": res_data["physical_exam"],
                "diagnosis": res_data["diagnosis"],
                "plan": res_data["plan"],
                "icd10_code": res_data["icd10_code"],
                "icd10_description": res_data["icd10_description"],
                "prescription": {
                    "items": [
                        {
                            "medication": "Ibuprofeno",
                            "dosage": "600 mg",
                            "frequency": "Cada 8 horas",
                            "duration": "5 días",
                            "instructions": "Vía oral con alimentos",
                        }
                    ],
                    "diagnosis_summary": "Endometriosis ovárica",
                },
            },
            headers=doctor_headers,
        )
        assert finish_resp.status_code == 201
        created_rec = finish_resp.json()
        assert len(created_rec["attachments"]) >= 1
        assert created_rec["attachments"][0]["id"] == audio_attachment_id

    finally:
        async with AsyncSessionLocal() as db:
            from app.models.medical_record import MedicalRecord
            from app.models.prescription import Prescription
            from app.models.medical_attachment import MedicalAttachment
            # Cleanup
            rec = (await db.execute(select(MedicalRecord).where(MedicalRecord.appointment_id == appointment_id))).scalar_one_or_none()
            if rec:
                prescs = (await db.execute(select(Prescription).where(Prescription.medical_record_id == rec.id))).scalars().all()
                for pr in prescs:
                    await db.delete(pr)
                atts = (await db.execute(select(MedicalAttachment).where(MedicalAttachment.medical_record_id == rec.id))).scalars().all()
                for a in atts:
                    await db.delete(a)
                await db.delete(rec)
            app_obj = await db.get(Appointment, appointment_id)

            if app_obj:
                await db.delete(app_obj)
            from app.models.audit import AuditLog
            from sqlalchemy import delete
            await db.execute(delete(AuditLog).where(AuditLog.user_id == doctor_id))

            d_obj = await db.get(User, doctor_id)
            if d_obj:
                await db.delete(d_obj)
            p_obj = await db.get(User, patient_id)
            if p_obj:
                await db.delete(p_obj)
            from app.models.clinic_encryption_key import ClinicEncryptionKey
            await db.execute(delete(ClinicEncryptionKey).where(ClinicEncryptionKey.clinic_id == clinic_id))

            c_obj = await db.get(Clinic, clinic_id)
            if c_obj:
                await db.delete(c_obj)
            await db.commit()


@pytest.mark.anyio
async def test_ai_consultation_assist_forbidden_when_consultation_assistant_disabled(client: AsyncClient):
    """Verifica que si la clínica tiene IA general habilitada pero NO el módulo de Consulta Asistida por IA, el endpoint responde 403."""
    from app.core.security import create_access_token
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic
    from app.models.appointment import Appointment
    from app.models.user import User
    import datetime

    admin_token = create_access_token(
        "u1111111-1111-1111-1111-111111111111",
        role="SUPERADMIN",
        email="admin@vitarecord.com",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    slug = f"clinica-no-assist-{uuid.uuid4().hex[:6]}"
    create_clinic_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica Solo IA Dictado",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
            "ai_enabled": True,
            "ai_api_url": "https://api.openai.com/v1/chat/completions",
            "ai_api_key": "sk-mock-key-for-test",
            "ai_model": "gpt-4o-mini",
            "ai_consultation_assistant_enabled": False,
        },
        headers=admin_headers,
    )
    assert create_clinic_resp.status_code == 201
    clinic_id = create_clinic_resp.json()["id"]

    doctor_id = str(uuid.uuid4())
    patient_id = str(uuid.uuid4())
    appointment_id = str(uuid.uuid4())

    async with AsyncSessionLocal() as db:
        doc_user = User(
            id=doctor_id,
            email=f"doc-no-assist-{uuid.uuid4().hex[:6]}@vitarecord.com",
            full_name="Dr. Juan Prueba",
            role="DOCTOR",
            specialty="Medicina Interna",
            hashed_password="hash",
            status="ACTIVE",
            license_verification_status="VERIFIED",
        )
        pat_user = User(
            id=patient_id,
            email=f"pat-no-assist-{uuid.uuid4().hex[:6]}@vitarecord.com",
            full_name="Paciente Prueba",
            role="PATIENT",
            hashed_password="hash",
            status="ACTIVE",
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        appt = Appointment(
            id=appointment_id,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            patient_id=patient_id,
            start_time=now,
            end_time=now + datetime.timedelta(minutes=30),
            status="IN_CONSULTATION",
            reason="Control general",
        )
        db.add_all([doc_user, pat_user, appt])
        await db.commit()

    try:
        doctor_token = create_access_token(
            doctor_id,
            role="DOCTOR",
            clinic_id=clinic_id,
            email=doc_user.email,
        )
        doctor_headers = {"Authorization": f"Bearer {doctor_token}"}

        # Intentar ejecutar la asistencia clínica con IA cuando el módulo está apagado
        resp = await client.post(
            "/api/v1/medical-records/ai-consultation-assist",
            json={
                "appointment_id": appointment_id,
                "transcript": "El paciente consulta por cefalea leve ocasional.",
                "doctor_specialty": "Medicina Interna",
            },
            headers=doctor_headers,
        )
        assert resp.status_code == 403
        assert "Consulta Asistida por IA no está activo" in resp.json()["detail"]

    finally:
        async with AsyncSessionLocal() as db:
            from app.models.audit import AuditLog
            from sqlalchemy import delete
            app_obj = await db.get(Appointment, appointment_id)
            if app_obj:
                await db.delete(app_obj)
            await db.execute(delete(AuditLog).where(AuditLog.user_id == doctor_id))
            d_obj = await db.get(User, doctor_id)
            if d_obj:
                await db.delete(d_obj)
            p_obj = await db.get(User, patient_id)
            if p_obj:
                await db.delete(p_obj)
            from app.models.clinic_encryption_key import ClinicEncryptionKey
            await db.execute(delete(ClinicEncryptionKey).where(ClinicEncryptionKey.clinic_id == clinic_id))
            c_obj = await db.get(Clinic, clinic_id)
            if c_obj:
                await db.delete(c_obj)
            await db.commit()


@pytest.mark.anyio
async def test_superadmin_can_update_clinic_modules(client: AsyncClient):
    """Verifica que el SuperAdmin puede activar e inactivar módulos específicos de la clínica."""
    from app.core.security import create_access_token
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic

    admin_token = create_access_token(
        "u1111111-1111-1111-1111-111111111111",
        role="SUPERADMIN",
        email="admin@vitarecord.com",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    slug = f"clinica-modules-{uuid.uuid4().hex[:6]}"
    create_clinic_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica Gestión Módulos",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
        },
        headers=admin_headers,
    )
    assert create_clinic_resp.status_code == 201
    clinic_id = create_clinic_resp.json()["id"]

    try:
        # Activar IA, Consulta asistida, y apagar Cashier mediante /modules
        modules_resp = await client.put(
            f"/api/v1/clinics/{clinic_id}/modules",
            json={
                "ai_enabled": True,
                "ai_consultation_assistant_enabled": True,
                "ai_model": "gpt-4o",
                "ai_api_url": "https://api.openai.com/v1/chat/completions",
                "ai_api_key": "sk-proj-modules-key-123456",
                "modules": {
                    "cashier": False,
                    "emergencies": True,
                    "prescriptions": True,
                },
                "require_mfa_for_receptionists": True,
            },
            headers=admin_headers,
        )
        assert modules_resp.status_code == 200
        data = modules_resp.json()
        assert data["ai_enabled"] is True
        assert data["ai_consultation_assistant_enabled"] is True
        assert data["require_mfa_for_receptionists"] is True
        assert data["active_modules"]["ai_assistant"] is True
        assert data["active_modules"]["ai_consultation"] is True
        assert data["active_modules"]["cashier"] is False
        assert data["active_modules"]["emergencies"] is True

        # Ahora apagar IA general y verificar que ai_consultation se apaga automáticamente
        off_resp = await client.put(
            f"/api/v1/clinics/{clinic_id}/modules",
            json={
                "ai_enabled": False,
            },
            headers=admin_headers,
        )
        assert off_resp.status_code == 200
        off_data = off_resp.json()
        assert off_data["ai_enabled"] is False
        assert off_data["ai_consultation_assistant_enabled"] is False
        assert off_data["active_modules"]["ai_assistant"] is False
        assert off_data["active_modules"]["ai_consultation"] is False

    finally:
        async with AsyncSessionLocal() as db:
            c_obj = await db.get(Clinic, clinic_id)
            if c_obj:
                await db.delete(c_obj)
            await db.commit()


@pytest.mark.anyio
async def test_superadmin_can_upload_and_delete_clinic_logo(client: AsyncClient):
    """Verifica que el SuperAdmin puede subir, consultar y eliminar el logotipo/avatar de una clínica."""
    from app.core.security import create_access_token
    from app.core.database import AsyncSessionLocal
    from app.models.clinic import Clinic

    admin_token = create_access_token(
        "u1111111-1111-1111-1111-111111111111",
        role="SUPERADMIN",
        email="admin@vitarecord.com",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    slug = f"clinica-logo-{uuid.uuid4().hex[:6]}"
    create_resp = await client.post(
        "/api/v1/clinics",
        json={
            "name": "Clínica Logo Test",
            "slug": slug,
            "timezone": "America/Caracas",
            "country_code": "VE",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    clinic_id = create_resp.json()["id"]

    try:
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        files = {"file": ("clinic_logo.png", dummy_png, "image/png")}

        # 1. Subir logotipo
        upload_resp = await client.post(
            f"/api/v1/clinics/{clinic_id}/logo",
            files=files,
            headers=admin_headers,
        )
        assert upload_resp.status_code == 200
        data = upload_resp.json()
        assert data["logo_url"] == f"/api/v1/clinics/{clinic_id}/logo"

        # 2. Servir logotipo públicamente
        get_resp = await client.get(f"/api/v1/clinics/{clinic_id}/logo")
        assert get_resp.status_code == 200
        assert "image/" in get_resp.headers["content-type"]

        # 3. Eliminar logotipo
        del_resp = await client.delete(
            f"/api/v1/clinics/{clinic_id}/logo",
            headers=admin_headers,
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["logo_url"] is None

        # 4. Comprobar que ya no existe
        get_del_resp = await client.get(f"/api/v1/clinics/{clinic_id}/logo")
        assert get_del_resp.status_code == 404

    finally:
        async with AsyncSessionLocal() as db:
            c_obj = await db.get(Clinic, clinic_id)
            if c_obj:
                await db.delete(c_obj)
            await db.commit()







