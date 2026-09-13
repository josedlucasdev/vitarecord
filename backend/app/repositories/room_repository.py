from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import ClinicRoom, RoomScheduleLock


class RoomRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_clinic(self, clinic_id: str, active_only: bool = False) -> list[ClinicRoom]:
        stmt = select(ClinicRoom).where(ClinicRoom.clinic_id == clinic_id)
        if active_only:
            stmt = stmt.where(ClinicRoom.is_active.is_(True))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, room_id: str) -> ClinicRoom | None:
        result = await self.db.execute(select(ClinicRoom).where(ClinicRoom.id == room_id))
        return result.scalar_one_or_none()

    async def create(self, room: ClinicRoom) -> ClinicRoom:
        self.db.add(room)
        await self.db.flush()

        # Fila mutex obligatoria para exclusion mutua en agendamiento fisico (plan/plan.md 2.B.4)
        lock = RoomScheduleLock(room_id=room.id)
        self.db.add(lock)
        await self.db.flush()

        return room

    async def update(self, room: ClinicRoom) -> ClinicRoom:
        await self.db.flush()
        return room

    async def deactivate(self, room_id: str) -> bool:
        room = await self.get_by_id(room_id)
        if room:
            room.is_active = False
            await self.db.flush()
            return True
        return False
