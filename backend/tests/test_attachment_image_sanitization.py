import io
import pytest
from httpx import AsyncClient
from PIL import Image

from app.core.image_processing import sanitize_and_convert_to_webp


def _create_jpeg_with_mock_exif() -> bytes:
    img = Image.new("RGB", (200, 200), color="red")
    exif = img.getexif()
    # Tag 0x010E es ImageDescription, Tag 0x0132 es DateTime
    exif[0x010E] = "Informacion sensible de paciente con EXIF y GPS"
    exif[0x0132] = "2026:09:25 12:00:00"

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_sanitize_and_convert_to_webp_strips_exif():
    jpeg_bytes = _create_jpeg_with_mock_exif()

    # Verificar que el JPEG de prueba tiene EXIF
    with Image.open(io.BytesIO(jpeg_bytes)) as original:
        orig_exif = original.getexif()
        assert 0x010E in orig_exif

    # Sanitizar y convertir
    webp_bytes, mime = sanitize_and_convert_to_webp(jpeg_bytes, max_dimension=1024)
    assert mime == "image/webp"

    # Verificar que la imagen resultante es WebP y NO contiene EXIF
    with Image.open(io.BytesIO(webp_bytes)) as sanitized:
        assert sanitized.format == "WEBP"
        sanitized_exif = sanitized.getexif()
        assert 0x010E not in sanitized_exif


@pytest.mark.anyio
async def test_avatar_upload_sanitizes_exif(client: AsyncClient):
    # 1. Login como Paciente
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "paciente@intimasalud.com", "password": "Password123!"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Subir avatar con EXIF en formato JPEG
    jpeg_bytes = _create_jpeg_with_mock_exif()
    files = {"file": ("avatar.jpg", jpeg_bytes, "image/jpeg")}

    resp = await client.post("/api/v1/patients/me/avatar", files=files, headers=headers)
    assert resp.status_code == 200
    assert "profile_picture_url" in resp.json()

    # 3. Descargar el avatar y comprobar que NO contiene EXIF
    get_resp = await client.get(resp.json()["profile_picture_url"])
    assert get_resp.status_code == 200
    assert get_resp.headers["content-type"] in ("image/jpeg", "image/webp")

    with Image.open(io.BytesIO(get_resp.content)) as downloaded:
        sanitized_exif = downloaded.getexif()
        assert 0x010E not in sanitized_exif

