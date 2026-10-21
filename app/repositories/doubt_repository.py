from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.doubt_model import Doubt

class DoubtRepository:
    async def create(self, session: AsyncSession, doubt: Doubt) -> Doubt:
        session.add(doubt)
        await session.commit()
        await session.refresh(doubt)
        return doubt 

    async def get_by_id(self, session: AsyncSession, doubt_id: int) -> Doubt | None:
        stmt = select(Doubt).where(Doubt.id == doubt_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, session: AsyncSession, course_id: int | None = None) -> list[Doubt]:
        stmt = select(Doubt)
        if course_id is not None:
            stmt = stmt.where(Doubt.course_id == course_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())
