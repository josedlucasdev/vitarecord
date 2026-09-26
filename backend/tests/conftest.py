import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import engine
from app.main import app

settings.ENVIRONMENT = "testing"
# Las cuentas sembradas (seed.py) no tienen MFA; la politica de MFA
# obligatorio se prueba de forma explicita en test_security_hardening.py.
settings.MFA_ENFORCEMENT_ENABLED = False
# Los tests de login social usan tokens emulados dev_fb_* / dev_google_*.
settings.ALLOW_DEV_SOCIAL_LOGIN = True


async def _clear_login_guard_counters() -> None:
    """Evita que intentos fallidos de un test bloqueen cuentas en otro."""
    try:
        import app.core.redis as r_mod

        redis = r_mod.get_redis()
        keys = [k async for k in redis.scan_iter("login:*")]
        if keys:
            await redis.delete(*keys)
    except Exception:
        pass


@pytest.fixture
async def client():
    await _clear_login_guard_counters()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    try:
        import app.core.redis as r_mod
        if r_mod._redis_client:
            await r_mod._redis_client.aclose()
        r_mod._redis_client = None
    except Exception:
        pass
    await engine.dispose()
