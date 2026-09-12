from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Motor de escritura/lectura por defecto. El enrutamiento a réplicas de
# lectura (plan/plan.md seccion 2.A) se añade en el Módulo 7 junto con la
# infraestructura de producción; en desarrollo un único engine es correcto.
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
