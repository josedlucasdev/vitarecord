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

        # 2. Configurar IA para la clínica con modelo específico
        ai_resp = await client.put(
            f"/api/v1/clinics/{clinic_id}/ai-settings",
            json={
                "ai_enabled": True,
                "ai_api_url": "https://api.openai.com/v1/chat/completions",
                "ai_api_key": "sk-proj-secret-key-test-123456",
                "ai_model": "gpt-4o",
            },
            headers=admin_headers,
        )
        assert ai_resp.status_code == 200
        ai_data = ai_resp.json()
        assert ai_data["ai_enabled"] is True
        assert ai_data["ai_api_url"] == "https://api.openai.com/v1/chat/completions"
        assert ai_data["has_ai_key"] is True
        assert ai_data["ai_model"] == "gpt-4o"
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

