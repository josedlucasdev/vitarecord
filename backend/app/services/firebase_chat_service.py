import asyncio
import json
import logging
import os
import time
from typing import Any
import httpx
from jose import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


class FirebaseChatService:
    """
    Servicio de sincronización en tiempo real para el chat de soporte con Firebase Realtime Database.
    Permite publicar mensajes y cambios de estado de forma instantánea hacia el widget web.
    """

    def __init__(self) -> None:
        self.credentials_file = settings.FIREBASE_CREDENTIALS_FILE
        self.database_url = settings.FIREBASE_DATABASE_URL.rstrip("/")
        self._cached_token: str | None = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        has_file = bool(self.credentials_file and os.path.exists(self.credentials_file))
        has_json = bool(settings.FCM_SERVICE_ACCOUNT_JSON)
        return bool((has_file or has_json) and self.database_url)

    async def _get_access_token(self) -> str | None:
        """Obtiene o renueva el token Bearer OAuth2 de Google Cloud mediante el Service Account."""
        now = time.time()
        if self._cached_token and now < (self._token_expires_at - 120):
            return self._cached_token

        if not self.is_configured():
            return None

        try:
            sa = None
            if self.credentials_file and os.path.exists(self.credentials_file):
                with open(self.credentials_file, "r") as f:
                    sa = json.load(f)
            elif settings.FCM_SERVICE_ACCOUNT_JSON:
                sa = json.loads(settings.FCM_SERVICE_ACCOUNT_JSON)

            if not sa or not sa.get("client_email") or not sa.get("private_key"):
                logger.warning("Credenciales de Firebase inválidas o incompletas.")
                return None

            now_int = int(now)
            payload = {
                "iss": sa["client_email"],
                "sub": sa["client_email"],
                "aud": "https://oauth2.googleapis.com/token",
                "iat": now_int,
                "exp": now_int + 3600,
                "scope": (
                    "https://www.googleapis.com/auth/firebase.database "
                    "https://www.googleapis.com/auth/userinfo.email"
                ),
            }
            assertion = jwt.encode(payload, sa["private_key"], algorithm="RS256")
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": assertion,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    self._cached_token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)
                    self._token_expires_at = now + expires_in
                    return self._cached_token
                logger.error("Error obteniendo token OAuth2 para Firebase RTDB: %s", res.text)
                return None
        except Exception as exc:
            logger.exception("Excepción obteniendo OAuth2 token para Firebase: %s", exc)
            return None

    async def publish_message(self, session_token: str, message_data: dict[str, Any]) -> bool:
        """
        Escribe el nuevo mensaje en la ruta:
        /support_chats/{session_token}/messages/{msg_id}.json
        """
        token = await self._get_access_token()
        if not token:
            logger.warning("Firebase Chat no configurado o sin token. No se publicó el mensaje.")
            return False

        msg_id = message_data.get("id")
        if not msg_id:
            logger.warning("Mensaje sin ID no puede ser publicado en Firebase.")
            return False

        clean_token = session_token.strip()
        url = f"{self.database_url}/support_chats/{clean_token}/messages/{msg_id}.json"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.put(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    json=message_data,
                )
                if res.status_code == 200:
                    return True
                logger.error("Error al escribir mensaje en Firebase RTDB: %s - %s", res.status_code, res.text)
                return False
        except Exception as exc:
            logger.exception("Error de red conectando con Firebase RTDB: %s", exc)
            return False

    async def publish_session_status(self, session_token: str, status: str, rated: bool = False) -> bool:
        """
        Actualiza el estado de la sesión en:
        /support_chats/{session_token}/status.json
        """
        token = await self._get_access_token()
        if not token:
            return False

        clean_token = session_token.strip()
        url = f"{self.database_url}/support_chats/{clean_token}/status.json"
        payload = {
            "session_token": clean_token,
            "status": status,
            "rated": rated,
            "updated_at": int(time.time()),
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.put(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )
                return res.status_code == 200
        except Exception as exc:
            logger.exception("Error al actualizar estado en Firebase RTDB: %s", exc)
            return False


firebase_chat_service = FirebaseChatService()
