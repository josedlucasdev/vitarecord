import uuid
import pytest
from httpx import AsyncClient

from app.core.database import AsyncSessionLocal
from app.models.user import User


@pytest.mark.anyio
async def test_google_login_new_patient(client: AsyncClient):
    """Verifica que el login con Google cree un nuevo paciente automáticamente y entregue tokens JWT."""
    google_uid = uuid.uuid4().hex[:12]
    dev_credential = f"dev_google_{google_uid}"

    resp = await client.post("/api/v1/auth/google", json={"credential": dev_credential})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Verificar creación del usuario en base de datos
    expected_email = f"paciente_google_{google_uid[:8]}@example.com"
    async with AsyncSessionLocal() as db:
        from app.repositories.user_repository import UserRepository
        user = await UserRepository(db).get_by_email(expected_email)
        assert user is not None
        assert user.role == "PATIENT"
        assert user.status == "ACTIVE"


@pytest.mark.anyio
async def test_google_login_existing_patient(client: AsyncClient):
    """Verifica que el login subsecuente con Google reutilice la cuenta existente."""
    google_uid = uuid.uuid4().hex[:12]
    dev_credential = f"dev_google_{google_uid}"

    # Primer login (crea)
    resp1 = await client.post("/api/v1/auth/google", json={"credential": dev_credential})
    assert resp1.status_code == 200

    # Segundo login (autentica)
    resp2 = await client.post("/api/v1/auth/google", json={"credential": dev_credential})
    assert resp2.status_code == 200
    assert "access_token" in resp2.json()
