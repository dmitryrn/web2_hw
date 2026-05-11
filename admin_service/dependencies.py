from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db import Database
from repositories import AdminRepository
from services import AuthService
from settings import Settings, load_settings


@dataclass
class AppContainer:
    settings: Settings
    database: Database


def build_container(settings: Settings | None = None) -> AppContainer:
    resolved_settings = settings or load_settings()
    return AppContainer(
        settings=resolved_settings,
        database=Database.from_url(resolved_settings.database_url),
    )


@asynccontextmanager
async def lifespan(app) -> AsyncIterator[None]:
    container = build_container()
    app.state.container = container
    try:
        yield
    finally:
        await container.database.dispose()


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_settings(request: Request) -> Settings:
    return get_container(request).settings


def get_database(request: Request) -> Database:
    return get_container(request).database


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database = get_database(request)
    async with database.session_factory() as session:
        yield session


def get_admin_repository(
    session: AsyncSession = Depends(get_session),
) -> AdminRepository:
    return AdminRepository(session)


def get_auth_service(
    repository: AdminRepository = Depends(get_admin_repository),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(repository, settings)


def get_auth_controller(
    service: AuthService = Depends(get_auth_service),
) -> "AuthController":
    from controllers.auth import AuthController

    return AuthController(service)
