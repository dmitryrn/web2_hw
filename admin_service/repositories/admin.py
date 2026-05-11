from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import AdminUser


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> AdminUser | None:
        return await self._session.scalar(
            select(AdminUser).where(AdminUser.username == username)
        )

    async def create(self, *, username: str, password_hash: str) -> AdminUser:
        admin = AdminUser(username=username, password_hash=password_hash)
        self._session.add(admin)
        await self._session.commit()
        await self._session.refresh(admin)
        return admin
