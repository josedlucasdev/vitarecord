import io
import json
import pytest
from httpx import AsyncClient
from PIL import Image


@pytest.mark.anyio
async def test_user_settings_profile_and_avatar(client: AsyncClient):
    # 1. Login as standard user (patient)
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Get profile
    me_res = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "paciente@intimasalud.com"
    assert "role" in me_data
    assert "mfa_enabled" in me_data

    # 3. Update profile with first_name and last_name
    update_res = await client.put(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"first_name": "Lucía Elena", "last_name": "Rodríguez Silva", "phone": "+584129998877"},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["full_name"] == "Lucía Elena Rodríguez Silva"
    assert updated_data["phone"] == "+584129998877"

    # 4. Upload Avatar
    img_byte_arr = io.BytesIO()
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(img_byte_arr, format="PNG")
    avatar_bytes = img_byte_arr.getvalue()

    upload_res = await client.post(
        "/api/v1/auth/me/avatar",
        headers=auth_headers,
        files={"file": ("avatar.png", avatar_bytes, "image/png")},
    )
    assert upload_res.status_code == 200
    avatar_url = upload_res.json()["profile_picture_url"]
    assert "avatar" in avatar_url

    # Check that avatar is served
    avatar_fetch = await client.get(avatar_url)
    assert avatar_fetch.status_code == 200
    assert len(avatar_fetch.content) > 0

    # 5. Delete Avatar
    del_res = await client.delete("/api/v1/auth/me/avatar", headers=auth_headers)
    assert del_res.status_code == 200

    me_check = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_check.json()["profile_picture_url"] is None


@pytest.mark.anyio
async def test_recovery_methods_and_backup_codes(client: AsyncClient):
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "recepcion@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == 200
    auth_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 1. Consult recovery methods
    rec_res = await client.get("/api/v1/auth/recovery-methods", headers=auth_headers)
    assert rec_res.status_code == 200

    # 2. Update recovery email and phone
    put_rec = await client.put(
        "/api/v1/auth/recovery-methods",
        headers=auth_headers,
        json={"recovery_email": "respaldo.recepcion@example.com", "recovery_phone": "+584145550011"},
    )
    assert put_rec.status_code == 200
    data = put_rec.json()
    assert data["recovery_email"] == "respaldo.recepcion@example.com"
    assert data["recovery_phone"] == "+584145550011"

    # 3. Generate backup codes
    gen_res = await client.post("/api/v1/auth/recovery-codes/generate", headers=auth_headers)
    assert gen_res.status_code == 200
    codes_data = gen_res.json()
    assert len(codes_data["codes"]) == 8
    assert "-" in codes_data["codes"][0]

    # Verify recovery methods now reflects backup codes exist
    rec_check = await client.get("/api/v1/auth/recovery-methods", headers=auth_headers)
    assert rec_check.json()["has_recovery_codes"] is True
    assert rec_check.json()["recovery_codes_count"] == 8


@pytest.mark.anyio
async def test_granular_notification_settings(client: AsyncClient):
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "moderador@vitarecord.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == 200
    auth_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 1. Get current settings
    notif_res = await client.get("/api/v1/auth/notification-settings", headers=auth_headers)
    assert notif_res.status_code == 200
    pref = notif_res.json()
    assert "channels" in pref
    assert "categories" in pref
    assert "appointments" in pref["categories"]

    # 2. Update granular categories and channels
    update_payload = {
        "channels": ["EMAIL", "PUSH"],
        "categories": {
            "appointments": {"email": True, "push": True, "whatsapp": False},
            "emergencies": {"email": True, "push": True, "whatsapp": True},
            "clinical_records": {"email": True, "push": False, "whatsapp": False},
            "security": {"email": True, "push": True, "whatsapp": False},
        },
    }
    put_res = await client.put("/api/v1/auth/notification-settings", headers=auth_headers, json=update_payload)
    assert put_res.status_code == 200
    saved = put_res.json()
    assert saved["channels"] == ["EMAIL", "PUSH"]
    assert saved["categories"]["appointments"]["whatsapp"] is False


@pytest.mark.anyio
async def test_data_export_and_account_deletion(client: AsyncClient):
    # 1. Create a dummy patient user to test export and deletion
    login_patient = await client.post(
        "/api/v1/auth/login",
        data={"username": "clinic.admin@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_patient.status_code == 200
    auth_headers = {"Authorization": f"Bearer {login_patient.json()['access_token']}"}

    # 2. Export data (GDPR Portability)
    export_res = await client.get("/api/v1/auth/me/export", headers=auth_headers)
    assert export_res.status_code == 200
    assert "attachment;" in export_res.headers.get("content-disposition", "")
    export_data = export_res.json()
    assert "metadata" in export_data
    assert "user_profile" in export_data
    assert export_data["metadata"]["compliance"] != ""

    # 3. Test deletion validation: wrong password fails
    del_fail = await client.post(
        "/api/v1/auth/me/delete-account",
        headers=auth_headers,
        json={"password": "WrongPassword999!"},
    )
    assert del_fail.status_code == 400
    assert "contraseña" in del_fail.json()["detail"].lower()


@pytest.mark.anyio
async def test_full_account_deletion_flow(client: AsyncClient):
    import uuid
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User

    unique_email = f"test_delete_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "Password123!"

    async with AsyncSessionLocal() as db:
        new_user = User(
            email=unique_email,
            full_name="Usuario Para Borrar",
            phone="+584129990000",
            hashed_password=hash_password(pwd),
            role="PATIENT",
            status="ACTIVE",
        )
        db.add(new_user)
        await db.commit()

    # 1. Login with the freshly created test user
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": unique_email, "password": pwd},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Request permanent account deletion with correct password
    del_res = await client.post(
        "/api/v1/auth/me/delete-account",
        headers=auth_headers,
        json={"password": pwd, "reason": "Cierre voluntario de cuenta de prueba"},
    )
    assert del_res.status_code == 200
    assert "eliminados y anonimizados" in del_res.json()["message"]

    # 3. Verify user can no longer log in with original credentials
    login_again = await client.post(
        "/api/v1/auth/login",
        data={"username": unique_email, "password": pwd},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_again.status_code == 401
