from typing import Any

from beanie import PydanticObjectId
import bson.errors
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from starlette import status

from src.schemas.users import Role
from src.utils import auth_utils
from src.models.users import User
from src.services import users as users_service, auth as auth_service


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def check_bearer_token(token: str, exception_to_raise: Exception) -> dict[str, Any]:
    """Checks whether given bearer token is valid or not. Raises the given exception instance if invalid."""

    try:
        token_data = auth_utils.parse_bearer_token(token)
    except JWTError:
        raise exception_to_raise

    return token_data


async def check_access_token(access_token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """Checks whether the access token was signed by this server and whether its still valid.
    Raises a 403 error if any of the checks fails."""

    forbidden_error = HTTPException(status.HTTP_403_FORBIDDEN)

    token_data = check_bearer_token(access_token, forbidden_error)

    blacklisted_token = await auth_service.get_blacklisted_token(access_token)
    if blacklisted_token is not None:
        raise forbidden_error

    return token_data


async def get_current_user(token_data: dict[str, Any] = Depends(check_access_token)) -> User:
    """Checks whether the `user_id` inside the token is valid and whether the user exists or not, returning the user
    instance. Raises a 403 error if any of the checks fails."""

    forbidden_error = HTTPException(status.HTTP_403_FORBIDDEN)

    try:
        user_id = PydanticObjectId(token_data["sub"])
    except bson.errors.InvalidId:
        raise forbidden_error

    user = await users_service.get_user_from_database(user_id, False)
    if user is None:
        raise forbidden_error

    return user


async def check_access_to_user_resource(input_user_id: PydanticObjectId, user: User) -> None:
    """Checks whether the current user has access to the current `User` resource."""

    forbidden_error = HTTPException(status.HTTP_403_FORBIDDEN)

    if user.role != Role.admin and user.id != input_user_id:
        raise forbidden_error
