from repositories import AdminRepository
from security import create_access_token, verify_password
from settings import Settings


class AuthService:
    def __init__(self, admin_repo: AdminRepository, settings: Settings) -> None:
        self._admin_repo = admin_repo
        self._settings = settings

    async def login(self, *, username: str, password: str) -> str | None:
        admin = await self._admin_repo.get_by_username(username)
        if admin is None or not verify_password(password, admin.password_hash):
            return None

        return create_access_token(
            subject=admin.username,
            jwt_secret=self._settings.jwt_secret,
            jwt_expires_minutes=self._settings.jwt_expires_minutes,
        )
