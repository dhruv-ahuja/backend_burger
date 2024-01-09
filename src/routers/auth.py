from typing import Any

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from starlette import status

from src import dependencies as deps
from src.config.constants import app
from src.models.users import User
from src.schemas.responses import AppResponse, BaseResponse
from src.schemas.web_responses import auth as resp
from src.services import auth as service
from src.utils import auth_utils


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", responses=resp.LOGIN_RESPONSES)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Logs the user into the application, checking first whether user credentials."""

    logger.info("attempting user login")

    user = await service.check_users_credentials(form_data)
    access_token = auth_utils.create_bearer_token(app.ACCESS_TOKEN_DURATION, str(user.id))
    refresh_token = auth_utils.create_bearer_token(app.REFRESH_TOKEN_DURATION, str(user.id))

    response = BaseResponse(data={"access_token": access_token, "refresh_token": refresh_token, "type": "Bearer"})
    return AppResponse(response)


@router.get("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=resp.LOGOUT_RESPONSES)
async def logout(
    access_token: str = Depends(deps.oauth2_scheme),
    token_data: dict[str, Any] = Depends(deps.check_access_token),
    user: User = Depends(deps.get_current_user),
):
    """Logs the current user out of the application."""

    await service.blacklist_access_token(user, access_token, token_data["exp"])
