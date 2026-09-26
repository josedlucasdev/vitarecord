"""Orquestador periódico de escalamiento de urgencias (plan/plan.md 2.B.7).

Cada EMERGENCY_CHECK_INTERVAL_SECONDS evalúa los incidentes sin médico
asignado y aplica los SLA (15 s refuerzo por voz, 60 s siguiente médico,
2 min moderador -> línea de respaldo). Un cerrojo en Redis garantiza que solo
una réplica del backend ejecute cada ciclo.
"""

import asyncio
import logging

from app.core.config import settings
from app.core.redis import get_redis
from app.services.emergency_service import process_emergency_escalations

logger = logging.getLogger("emergency_escalation")

LOCK_KEY = "lock:emergency_escalation_scan"


async def start_emergency_escalation_scheduler(interval_seconds: int | None = None) -> None:
    interval = max(1, interval_seconds or settings.EMERGENCY_CHECK_INTERVAL_SECONDS)
    logger.info("Iniciando orquestador de escalamiento de urgencias (intervalo: %ds)", interval)
    while True:
        try:
            acquired = True
            try:
                acquired = bool(await get_redis().set(LOCK_KEY, "1", nx=True, ex=max(1, interval - 1)))
            except Exception as exc:  # noqa: BLE001
                # Sin Redis se sigue escalando (mejor duplicar una llamada que no escalar).
                logger.warning("Cerrojo de escalamiento sin Redis, se ejecuta igual: %s", exc)
            if acquired:
                stats = await process_emergency_escalations()
                if stats["escalations"] or stats["reinforcements"]:
                    logger.info("Ciclo de escalamiento de urgencias: %s", stats)
        except asyncio.CancelledError:
            logger.info("Orquestador de escalamiento cancelado.")
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error en ciclo de escalamiento de urgencias: %s", exc)
        await asyncio.sleep(interval)
