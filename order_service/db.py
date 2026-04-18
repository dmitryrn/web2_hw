from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from settings import settings


engine_kwargs = {"echo": True}
if settings.database_url.startswith("postgresql+asyncpg://"):
    engine_kwargs["connect_args"] = {"server_settings": {"TimeZone": "UTC"}}

engine = create_async_engine(settings.database_url, **engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
