from typing import Any

from beanie import PydanticObjectId
import bson.errors
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from starlette import status

from src.utils import auth_utils
from src.models.users import User
from src.services import users as users_service, auth as auth_service


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def check_access_token(access_token: str = Depends(oauth2_scheme)) -> dict[str, Any] | None:
    """Checks whether the access token was signed by this server and whether its still valid.
    Returns `None` if the token is invalid, else the token data dictionary."""

    try:
        token_data = auth_utils.parse_access_token(access_token)
    except JWTError:
        return None

    blacklisted_token = await auth_service.get_blacklisted_token(access_token)
    if blacklisted_token is not None:
        return None

    return token_data


async def get_current_user(token_data: dict[str, Any] | None = Depends(check_access_token)) -> User:
    """Checks whether the `user_id` inside the token is valid and whether the user exists or not, returning the user
    instance. Raises a 403 error if any of the checks fails."""

    forbidden_error = HTTPException(status.HTTP_403_FORBIDDEN)

    if token_data is None:
        raise forbidden_error

    try:
        user_id = PydanticObjectId(token_data["sub"])
    except bson.errors.InvalidId:
        raise forbidden_error

    user = await users_service.get_user_from_database(user_id, False)
    if user is None:
        raise forbidden_error

    return user
