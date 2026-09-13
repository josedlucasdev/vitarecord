"""WebSocket Connection Manager y Redis Pub/Sub para Notificaciones In-App en tiempo real por usuario."""

import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket
from app.core.redis import get_redis

logger = logging.getLogger("notification_hub")

USER_NOTIFICATIONS_CHANNEL = "user_notifications_broadcast"


class NotificationHub:
    def __init__(self):
        # Mapeo: user_id -> set de WebSockets activos (múltiples pestañas o dispositivos)
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        self._listener_task: asyncio.Task | None = None

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        logger.info(f"[NotificationHub] Usuario {user_id} conectado. Conexiones del usuario: {len(self.user_connections[user_id])}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        logger.info(f"[NotificationHub] Desconectado socket de usuario {user_id}")

    async def send_to_user_local(self, user_id: str, payload: dict):
        """Envía el payload a todos los websockets locales activos de un usuario."""
        connections = self.user_connections.get(user_id, set())
        dead_connections = set()
        for ws in list(connections):
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.warning(f"[NotificationHub] Error enviando a socket de {user_id}: {e}")
                dead_connections.add(ws)

        for dead in dead_connections:
            self.disconnect(user_id, dead)

    async def notify_user(self, user_id: str, event_type: str, data: dict):
        """Notifica a un usuario específico tanto localmente como vía Redis Pub/Sub."""
        payload = {
            "recipient_id": user_id,
            "event": event_type,
            "data": data,
        }

        # Envío local inmediato
        await self.send_to_user_local(user_id, payload)

        # Difusión en Redis para instancias concurrentes
        try:
            r = get_redis()
            await r.publish(USER_NOTIFICATIONS_CHANNEL, json.dumps(payload, default=str))
        except Exception as e:
            logger.error(f"[NotificationHub] Error publicando en Redis: {e}")

    async def start_redis_listener(self):
        """Tarea asíncrona en segundo plano para escuchar eventos distribuidos en Redis."""
        try:
            r = get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe(USER_NOTIFICATIONS_CHANNEL)
            logger.info("[NotificationHub] Suscrito al canal Redis de notificaciones in-app.")

            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    try:
                        raw = message.get("data")
                        if isinstance(raw, (str, bytes)):
                            payload = json.loads(raw)
                            recipient_id = payload.get("recipient_id")
                            if recipient_id and recipient_id in self.user_connections:
                                await self.send_to_user_local(recipient_id, payload)
                    except Exception as parse_err:
                        logger.warning(f"[NotificationHub] Error procesando mensaje de Redis: {parse_err}")
        except asyncio.CancelledError:
            logger.info("[NotificationHub] Listener de Redis cancelado limpiamente.")
        except Exception as e:
            logger.error(f"[NotificationHub] Error fatal en listener de Redis: {e}")


notification_hub = NotificationHub()
