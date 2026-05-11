from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import get_auth_controller
from schemas import LoginRequest, TokenResponse
from services import AuthService


router = APIRouter()


class AuthController:
    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    async def login(self, payload: LoginRequest) -> TokenResponse:
        token = await self._auth_service.login(
            username=payload.username,
            password=payload.password,
        )
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    controller: AuthController = Depends(get_auth_controller),
) -> TokenResponse:
    return await controller.login(payload)
