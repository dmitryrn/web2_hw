from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    engine_kwargs = {"echo": True}
    if database_url.startswith("postgresql+asyncpg://"):
        engine_kwargs["connect_args"] = {"server_settings": {"TimeZone": "UTC"}}
    return create_async_engine(database_url, **engine_kwargs)


def create_session_factory(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    database_engine = create_engine(database_url)
    session_factory = async_sessionmaker(
        database_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    return database_engine, session_factory


@dataclass
class Database:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    @classmethod
    def from_url(cls, database_url: str) -> "Database":
        engine, session_factory = create_session_factory(database_url)
        return cls(engine=engine, session_factory=session_factory)

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session

    async def dispose(self) -> None:
        await self.engine.dispose()


async def get_session(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.session_factory() as session:
        yield session
