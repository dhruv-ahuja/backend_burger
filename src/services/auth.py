import datetime as dt

from beanie import PydanticObjectId
import bson.errors
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from starlette import status

from src.models.auth import BlacklistedTokens
from src.models.users import User
from src.services import users as users_service
from src.utils.auth_utils import compare_values


async def check_users_credentials(form_data: OAuth2PasswordRequestForm) -> User:
    """Checks whether the given credentials are valid, and whether the user exists. Returns the user on success."""

    invalid_credentials_error = HTTPException(status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Bearer"})

    try:
        user_id = PydanticObjectId(form_data.username)
    except bson.errors.InvalidId:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid user_id")

    user = await users_service.get_user_from_database(user_id, False)
    if user is None:
        raise invalid_credentials_error

    password = form_data.password
    valid_password = compare_values(password, user.password.get_secret_value())

    if not valid_password:
        raise invalid_credentials_error

    return user


async def blacklist_token(user: User, token: str, expiration_time: dt.datetime) -> None:
    """Adds a token to the BlacklistTokens records, marking it as invalid for the application."""

    blacklist_record = BlacklistedTokens(user=user, token=token, expiration_time=expiration_time)  # type: ignore

    try:
        await blacklist_record.insert()  # type: ignore
    except Exception as ex:
        print(f"error adding token to blacklist: {ex}")
        logger.error(f"error adding token to blacklist: {ex}")
        raise
