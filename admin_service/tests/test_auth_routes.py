import asyncio
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import jwt
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-with-at-least-32-bytes")

import db as db_module
import dependencies as dependency_module
import main as app_module
from models import Base
from repositories import AdminRepository
from security import hash_password, verify_password


@pytest.fixture
def client() -> Iterator[TestClient]:
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def override_get_session():
        async with session_factory() as session:
            yield session

    async def prepare_db() -> None:
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            repo = AdminRepository(session)
            await repo.create(username="admin", password_hash=hash_password("admin"))

    app_module.app.dependency_overrides[dependency_module.get_session] = override_get_session

    try:
        asyncio.run(prepare_db())
        with TestClient(app_module.app) as test_client:
            yield test_client
    finally:
        app_module.app.dependency_overrides.clear()
        asyncio.run(test_engine.dispose())


def test_login_returns_jwt_for_seeded_admin(client: TestClient) -> None:
    response = client.post("/login", json={"username": "admin", "password": "admin"})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2

    payload = jwt.decode(
        body["access_token"],
        "test-secret-with-at-least-32-bytes",
        algorithms=["HS256"],
    )
    assert payload["sub"] == "admin"
    assert payload["exp"] > payload["iat"]


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post("/login", json={"username": "admin", "password": "wrong"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_hash_password_uses_bcrypt() -> None:
    password_hash = hash_password("admin")

    assert password_hash.startswith("$2b$")
    assert verify_password("admin", password_hash)
    assert not verify_password("wrong", password_hash)


def test_importing_db_does_not_configure_database() -> None:
    assert not hasattr(db_module, "SessionLocal")
