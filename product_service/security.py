import logging
from contextvars import ContextVar

import jwt
from fastapi import Header, HTTPException, status

from settings import settings


logger = logging.getLogger(__name__)
current_authorization: ContextVar[str] = ContextVar("current_authorization", default="")


def auth_headers_from_request() -> dict[str, str]:
    authorization = current_authorization.get()
    if not authorization:
        return {}

    return {"Authorization": authorization}


def validate_authorization(authorization: str) -> None:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        logger.warning("JWT authentication failed: missing bearer token")

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.warning("JWT authentication failed: token has expired")

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError:
        logger.warning("JWT authentication failed: invalid token")

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


async def require_jwt(authorization: str = Header(default="")) -> None:
    validate_authorization(authorization)
    current_authorization.set(authorization)
