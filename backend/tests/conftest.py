import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import engine
from app.main import app

settings.ENVIRONMENT = "testing"


@pytest.fixture
async def client():
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
