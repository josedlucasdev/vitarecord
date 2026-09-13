"""Cliente de conexion asincrono a Redis (plan/plan.md seccion 2.A y 2.B.4)."""

import redis.asyncio as aioredis

from app.core.config import settings

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    try:
        import asyncio
        loop = asyncio.get_running_loop()
        if _redis_client is not None:
            pool = getattr(_redis_client, "connection_pool", None)
            if pool and hasattr(pool, "_loop") and pool._loop is not None and pool._loop != loop:
                _redis_client = None
    except Exception:
        pass

    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client
