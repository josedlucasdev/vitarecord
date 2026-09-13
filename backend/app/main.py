from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.observability import setup_observability
from app.core.tenant import reset_tenant_context  # registra el listener ORM al importarse
from app.db.seed import init_db_and_seed

setup_observability()


import asyncio
from app.core.emergency_hub import emergency_hub


@asynccontextmanager
async def lifespan(app: FastAPI):
    listener_task = None
    reminder_task = None
    notif_listener_task = None
    try:
        await init_db_and_seed()
        listener_task = asyncio.create_task(emergency_hub.start_redis_listener())
        from app.core.notification_hub import notification_hub
        notif_listener_task = asyncio.create_task(notification_hub.start_redis_listener())
        from app.tasks.reminders import start_reminder_scheduler
        reminder_task = asyncio.create_task(start_reminder_scheduler())
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("main").warning("No se pudo autosembrar la BD o iniciar tareas en arranque: %s", exc)
    yield
    if listener_task:
        listener_task.cancel()
    if notif_listener_task:
        notif_listener_task.cancel()
    if reminder_task:
        reminder_task.cancel()




app = FastAPI(title="ÍntimaSalud API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reset_tenant_context_per_request(request: Request, call_next):
    # Defensivo: cada peticion arranca sin contexto de tenant heredado de
    # una peticion anterior. app.api.deps.get_current_user lo vuelve a
    # establecer segun el JWT / cabecera X-Clinic-ID de ESTA peticion.
    reset_tenant_context()
    response = await call_next(request)
    reset_tenant_context()

    # Prevenir que navegadores almacenen en cache peticiones a los endpoints del API
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"

    return response


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


@app.get("/readiness", tags=["system"])
async def readiness():
    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        return {"status": "ready"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "not_ready", "detail": str(exc)}
