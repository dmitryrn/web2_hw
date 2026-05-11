import time

import bcrypt
import jwt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    *,
    subject: str,
    jwt_secret: str,
    jwt_expires_minutes: int,
) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": subject,
            "iat": now,
            "exp": now + jwt_expires_minutes * 60,
        },
        jwt_secret,
        algorithm="HS256",
    )
