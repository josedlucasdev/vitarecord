"""Proteccion del login contra fuerza bruta (plan/plan.md seccion 2.B.9).

Reglas:
- Backoff exponencial por cuenta: a partir del 3er intento fallido
  consecutivo se exige esperar 2^(n-2) segundos (maximo 30 s) antes del
  siguiente intento.
- Bloqueo temporal de la cuenta (LOGIN_LOCKOUT_MINUTES) tras
  LOGIN_MAX_ATTEMPTS fallos dentro de LOGIN_ATTEMPT_WINDOW_MINUTES.
- A partir del bloqueo numero LOGIN_CAPTCHA_AFTER_LOCKOUTS (por defecto el
  segundo) se exige CAPTCHA (Cloudflare Turnstile) mientras dure el
  historial de bloqueos (24 h), si TURNSTILE_SECRET_KEY esta configurado.
- Limite de intentos FALLIDOS por IP (LOGIN_MAX_ATTEMPTS_PER_IP en la
  ventana) para frenar ataques de "password spraying" contra muchas cuentas.

Los contadores se llevan por correo normalizado aunque la cuenta no exista,
para no revelar que correos estan registrados. Todo vive en Redis; si Redis
no esta disponible se deja pasar el intento (fail-open) y se registra un
warning: el hash Argon2id sigue siendo la barrera principal.
"""

from __future__ import annotations

import logging
import math

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger("login_guard")

LOCKOUT_HISTORY_SECONDS = 24 * 60 * 60
MAX_BACKOFF_SECONDS = 30
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

CAPTCHA_REQUIRED_DETAIL = "CAPTCHA_REQUIRED: Complete la verificación de seguridad para continuar."


def _norm(email: str) -> str:
    return (email or "").strip().lower()


def _keys(email: str, ip: str | None) -> dict[str, str]:
    e = _norm(email)
    return {
        "fails": f"login:fails:{e}",
        "lock": f"login:lock:{e}",
        "backoff": f"login:backoff:{e}",
        "lockouts": f"login:lockouts:{e}",
        "ip": f"login:ip:{ip or 'unknown'}",
    }


def _too_many(detail: str, retry_after: int) -> HTTPException:
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        detail,
        headers={"Retry-After": str(max(1, int(retry_after)))},
    )


async def _verify_captcha(token: str | None, ip: str | None) -> bool:
    if not settings.TURNSTILE_SECRET_KEY:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(
                TURNSTILE_VERIFY_URL,
                data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token, "remoteip": ip or ""},
            )
        return bool(res.json().get("success"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo verificar CAPTCHA: %s", exc)
        return False


async def check_login_allowed(email: str, ip: str | None, captcha_token: str | None = None) -> None:
    """Lanza 429/428 si el intento de login no debe procesarse."""
    k = _keys(email, ip)
    try:
        redis = get_redis()
        ip_count = int(await redis.get(k["ip"]) or 0)

        lock_ttl = await redis.ttl(k["lock"])
        backoff_ttl = await redis.ttl(k["backoff"])
        lockouts = int(await redis.get(k["lockouts"]) or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Proteccion de login sin Redis (fail-open): %s", exc)
        return

    if ip_count >= settings.LOGIN_MAX_ATTEMPTS_PER_IP:
        raise _too_many(
            "Demasiados intentos de inicio de sesión desde esta red. Intente más tarde.",
            settings.LOGIN_ATTEMPT_WINDOW_MINUTES * 60,
        )
    if lock_ttl and lock_ttl > 0:
        minutes = math.ceil(lock_ttl / 60)
        raise _too_many(
            f"Cuenta bloqueada temporalmente por intentos fallidos. Intente de nuevo en {minutes} minuto(s).",
            lock_ttl,
        )
    if backoff_ttl and backoff_ttl > 0:
        raise _too_many(
            f"Demasiados intentos seguidos. Espere {backoff_ttl} segundo(s) antes de reintentar.",
            backoff_ttl,
        )
    if lockouts >= settings.LOGIN_CAPTCHA_AFTER_LOCKOUTS and settings.TURNSTILE_SECRET_KEY:
        if not await _verify_captcha(captcha_token, ip):
            raise HTTPException(
                status.HTTP_428_PRECONDITION_REQUIRED,
                CAPTCHA_REQUIRED_DETAIL,
                headers={"X-Captcha-Required": "true"},
            )


async def register_login_failure(email: str, ip: str | None) -> None:
    k = _keys(email, ip)
    window = settings.LOGIN_ATTEMPT_WINDOW_MINUTES * 60
    try:
        redis = get_redis()
        ip_fails = await redis.incr(k["ip"])
        if ip_fails == 1:
            await redis.expire(k["ip"], window)
        fails = await redis.incr(k["fails"])
        if fails == 1:
            await redis.expire(k["fails"], window)

        if fails >= settings.LOGIN_MAX_ATTEMPTS:
            await redis.set(k["lock"], "1", ex=settings.LOGIN_LOCKOUT_MINUTES * 60)
            await redis.delete(k["fails"], k["backoff"])
            lockouts = await redis.incr(k["lockouts"])
            await redis.expire(k["lockouts"], LOCKOUT_HISTORY_SECONDS)
            logger.warning("Cuenta %s bloqueada por intentos fallidos (bloqueo #%s)", _norm(email), lockouts)
        elif fails >= 3:
            await redis.set(k["backoff"], "1", ex=min(2 ** (fails - 2), MAX_BACKOFF_SECONDS))
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo registrar el intento fallido: %s", exc)


async def register_login_success(email: str) -> None:
    k = _keys(email, None)
    try:
        await get_redis().delete(k["fails"], k["backoff"], k["lockouts"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo limpiar contadores de login: %s", exc)
