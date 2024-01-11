import datetime as dt

from beanie import PydanticObjectId
from beanie.operators import Set
import bson.errors
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from loguru import logger
from starlette import status

from src.models.users import User, BlacklistedToken, UserSession
from src.services import users as users_service
from src.utils.auth_utils import compare_values


async def check_users_credentials(form_data: OAuth2PasswordRequestForm) -> User:
    """Checks whether the given credentials are valid, and whether the user exists. Returns the user on success."""

    invalid_credentials_error = HTTPException(status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Bearer"})

    try:
        user_id = PydanticObjectId(form_data.username)
    except bson.errors.InvalidId:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid username")

    user = await users_service.get_user_from_database(user_id, False)
    if user is None:
        raise invalid_credentials_error

    password = form_data.password
    valid_password = compare_values(password, user.password.get_secret_value())

    if not valid_password:
        raise invalid_credentials_error

    return user


async def save_session_details(user: User, refresh_token: str, expiration_time: dt.datetime) -> None:
    """Saves users session details, storing the issued refresh token and its expiration time in the database.
    Re-uses an existing session record or creates a new one."""

    values_to_update = {
        UserSession.refresh_token: refresh_token,
        UserSession.expiration_time: expiration_time,
        UserSession.updated_time: dt.datetime.now(),
    }

    try:
        await UserSession.find_one(UserSession.user.id == user.id).upsert(  # type: ignore
            Set(values_to_update),
            on_insert=UserSession(user=user, refresh_token=refresh_token, expiration_time=expiration_time),  # type: ignore
        )
    except Exception as exc:
        logger.error(f"error saving user session details: {exc}")
        raise


async def blacklist_access_token(user: User, access_token: str, expiration_time: dt.datetime) -> None:
    """Adds an access token to the BlacklistTokens records, marking it as invalid for the application."""

    blacklist_record = BlacklistedToken(user=user, access_token=access_token, expiration_time=expiration_time)  # type: ignore

    try:
        await blacklist_record.insert()  # type: ignore
    except Exception as exc:
        logger.error(f"error adding token to blacklist: {exc}")
        raise


async def get_blacklisted_token(token: str) -> BlacklistedToken | None:
    """Fetches a blacklisted token from the database, given the token value."""

    try:
        blacklisted_token = await BlacklistedToken.find_one(BlacklistedToken.access_token == token)
    except Exception as exc:
        logger.error(f"error fetching blacklisted token: {exc}")
        raise

    return blacklisted_token


async def invalidate_refresh_token(user: User) -> None:
    """Removes the user's refresh token details from the database, invalidating it for the application."""

    values_to_update = {
        UserSession.refresh_token: None,
        UserSession.expiration_time: None,
        UserSession.updated_time: dt.datetime.now(),
    }

    try:
        await UserSession.find_one(UserSession.user.id == user.id).update(Set(values_to_update))  # type: ignore
    except Exception as exc:
        logger.error(f"error invalidating refresh token: {exc}")
        raise


async def get_user_session(user_id: str | None, user: User | None) -> UserSession | None:
    """Fetches a user session document from the database, given the user."""

    if user_id is None and user is None:
        raise ValueError("Invalid input. Pass either user or user_id.")

    if user_id is not None:
        user_id_ = PydanticObjectId(user_id)
    elif user is not None:
        user_id_ = user.id

    try:
        user_session = await UserSession.find_one(UserSession.user.id == user_id_)  # type: ignore
    except Exception as exc:
        logger.error(f"error fetching user session: {exc}")
        raise

    return user_session


async def delete_expired_blacklisted_tokens(delete_older_than: dt.datetime) -> None:
    """Deletes expired blacklisted tokens older than the given date range, from the database.
    Compares tokens' expiration times with the given date range."""

    logger.info(f"deleting expired blacklisted tokens older than {delete_older_than}")

    try:
        await BlacklistedToken.find_many(BlacklistedToken.expiration_time < delete_older_than).delete()
    except Exception as exc:
        logger.error(f"error deleting expired tokens: {exc}")
        raise
