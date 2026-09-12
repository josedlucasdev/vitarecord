"""WebSocket Connection Manager y Redis Pub/Sub para Torre de Control y Urgencias Médicas (plan/plan.md 2.B.7)."""

import asyncio
import json
import logging
from typing import Set
from fastapi import WebSocket
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

EMERGENCY_CHANNEL = "emergencies_broadcast"


class EmergencyHub:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._listener_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"[EmergencyHub] New client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"[EmergencyHub] Client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcasts a JSON message to all active WebSocket connections connected to this worker."""
        dead_connections = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"[EmergencyHub] Failed to send to socket: {e}")
                dead_connections.add(connection)
        
        for dead in dead_connections:
            self.disconnect(dead)

    async def publish_event(self, event_type: str, data: dict):
        """Publishes an emergency event to Redis Pub/Sub and also broadcasts locally."""
        payload = {
            "event": event_type,
            "data": data,
        }
        # Broadcast locally immediately
        await self.broadcast(payload)
        
        # Publish to Redis channel for multi-instance scalability
        try:
            redis = get_redis()
            await redis.publish(EMERGENCY_CHANNEL, json.dumps(payload, default=str))
        except Exception as e:
            logger.error(f"[EmergencyHub] Error publishing to Redis: {e}")

    async def start_redis_listener(self):
        """Background task to listen for events from Redis Pub/Sub."""
        try:
            redis = get_redis()
            pubsub = redis.pubsub()
            await pubsub.subscribe(EMERGENCY_CHANNEL)
            logger.info(f"[EmergencyHub] Subscribed to Redis channel: {EMERGENCY_CHANNEL}")
            
            async for message in pubsub.listen():
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self.broadcast(data)
                    except Exception as err:
                        logger.error(f"[EmergencyHub] Error handling redis message: {err}")
        except asyncio.CancelledError:
            logger.info("[EmergencyHub] Redis listener task cancelled.")
        except Exception as e:
            logger.warning(f"[EmergencyHub] Redis listener error (running in standalone/test mode): {e}")


# Global singleton instance
emergency_hub = EmergencyHub()
