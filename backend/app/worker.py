"""Worker autónomo en segundo plano para tareas asíncronas y schedulers (plan/plan.md Módulo 6).

Ejecuta de manera orquestada:
1. Schedulers periódicos protegidos por cerrojo distribuido Redis:
   - Recordatorios de citas (24h y 2h antes).
   - Escalamiento multinivel de urgencias médicas no atendidas.
   - Detección y transición legal diaria de dependientes emancipados (18 años).
2. Tareas encoladas a través del broker Taskiq / Redis.
"""

import asyncio
import logging
import signal

from app.core.broker import broker
from app.tasks.emancipation import start_emancipation_scheduler
from app.tasks.emergency_escalation import start_emergency_escalation_scheduler
from app.tasks.reminders import start_reminder_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger("worker")


async def main() -> None:
    logger.info("Iniciando contenedor dedicado de worker en segundo plano (VitaRecord)...")

    # Iniciar broker de Taskiq
    try:
        await broker.startup()
        logger.info("Broker Taskiq inicializado correctamente.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Broker Taskiq no pudo iniciar: %s", exc)

    # Lanzar los orquestadores periódicos con cerrojo distribuido
    tasks = [
        asyncio.create_task(start_reminder_scheduler(), name="reminders_scheduler"),
        asyncio.create_task(start_emergency_escalation_scheduler(), name="escalation_scheduler"),
        asyncio.create_task(start_emancipation_scheduler(), name="emancipation_scheduler"),
    ]

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _on_signal() -> None:
        logger.info("Señal de terminación recibida. Apagando schedulers...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _on_signal)
        except (NotImplementedError, RuntimeError):
            pass

    logger.info("Worker listo y ejecutando schedulers activamente.")
    await stop_event.wait()

    for t in tasks:
        t.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)
    try:
        await broker.shutdown()
    except Exception:  # noqa: BLE001
        pass

    logger.info("Worker detenido limpiamente.")


if __name__ == "__main__":
    asyncio.run(main())
