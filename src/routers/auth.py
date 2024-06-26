from typing import Any, cast

from fastapi import APIRouter, Body, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from motor.core import AgnosticClientSession
from redis.asyncio import Redis
from starlette import status

from src import dependencies as deps
from src.config.constants import app
from src.models.users import User
from src.schemas.responses import BaseResponse
from src.schemas.users import UserBase
from src.schemas.web_responses import auth as resp
from src.services import auth as service, users as users_service
from src.utils import auth_utils, services as services_utils


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", responses=resp.LOGIN_RESPONSES)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db_session: AgnosticClientSession = Depends(deps.get_db_session),
):
    """Logs the user into the application and caches their data, checking first whether user credentials are valid."""

    logger.info("attempting user login")
    user = await service.check_users_credentials(form_data)

    access_token, _ = auth_utils.create_bearer_token(app.ACCESS_TOKEN_DURATION, str(user.id))
    refresh_token, refresh_token_expiration_time = auth_utils.create_bearer_token(
        app.REFRESH_TOKEN_DURATION, str(user.id)
    )

    redis_client: Redis = request.app.state.redis
    redis_key = f"{app.USER_CACHE_KEY}:{user.id}"

    serialized_user = services_utils.serialize_response(BaseResponse(data=user))
    await services_utils.cache_data(redis_key, serialized_user, app.SINGLE_USER_CACHE_DURATION, redis_client)

    async with db_session.start_transaction():
        try:
            await services_utils.cache_data(redis_key, serialized_user, app.SINGLE_USER_CACHE_DURATION, redis_client)
        except Exception:
            raise

        await service.save_session_details(user, refresh_token, refresh_token_expiration_time, db_session)

    response = BaseResponse(data={"access_token": access_token, "refresh_token": refresh_token, "type": "Bearer"})
    return response


@router.get("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=resp.LOGOUT_RESPONSES)
async def logout(
    access_token: str = Depends(deps.oauth2_scheme),
    token_data: dict[str, Any] = Depends(deps.check_access_token),
    user_base: UserBase = Depends(deps.get_current_user),
    db_session: AgnosticClientSession = Depends(deps.get_db_session),
):
    """Logs the current user out of the application."""

    user = await users_service.get_user_from_database(user_base.id)
    user = cast(User, user)

    async with db_session.start_transaction():
        await service.invalidate_refresh_token(user, db_session)
        await service.blacklist_access_token(user, access_token, token_data["exp"], db_session)


@router.post("/token", responses=resp.TOKEN_RESPONSES)
async def refresh_token(refresh_token: str = Body(..., embed=True)):
    """Refreshes the user's access token, after checking whether the refresh token is valid and has not yet expired."""

    token_data = await deps.check_refresh_token(refresh_token)
    access_token, _ = auth_utils.create_bearer_token(app.ACCESS_TOKEN_DURATION, token_data["sub"])

    response = BaseResponse(data={"access_token": access_token, "type": "Bearer"})
    return response
