from typing import cast
from beanie import PydanticObjectId
from fastapi import HTTPException
from loguru import logger
from pydantic import SecretStr
from pymongo.errors import DuplicateKeyError
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.models.users import User
from src.schemas.users import UserBase, UserInput, UserUpdateInput
from src.utils import auth_utils


async def create_user(user_input: UserInput) -> PydanticObjectId | None:
    """Creates a user in the database, and returns the newly created user's ID."""

    hashed_password = auth_utils.hash_value(user_input.password.get_secret_value())
    user = User(name=user_input.name, email=user_input.email, password=SecretStr(hashed_password))

    try:
        user = await user.insert()
    except DuplicateKeyError:
        logger.error("error creating user: duplicate email used")
        raise HTTPException(HTTP_400_BAD_REQUEST, "Email associated with another account.")
    except Exception as ex:
        logger.error(f"error creating user: {ex}; error type: {ex.__class__}")
        raise

    return user.id


async def get_users() -> list[UserBase]:
    """Fetches users from the database, returning them as a list of UserBase instances."""

    try:
        user_records = await User.find_all().to_list()
    except Exception as ex:
        logger.error(f"error fetching users: {ex}; error_type: {ex.__class__}")
        raise

    users = []

    # parsing User to UserBase using parse_obj to avoid `id` loss -- pydantic V2 bug
    for user_record in user_records:
        user = UserBase(
            id=user_record.id,
            name=user_record.name,
            email=user_record.email,
            date_created=user_record.date_created,
            date_updated=user_record.date_updated,
        )
        users.append(user)

    return users


async def get_user_from_database(user_id: PydanticObjectId | None, missing_user_error: bool = True) -> User | None:
    """Fetches a user from the database, raising a 400 error if the given `user_id` is invalid. Raises a 404 error if
    the user does not exist and `missing_user_error` is `True`."""

    try:
        user = await User.get(user_id)
    except Exception as ex:
        logger.error(f"error fetching user: {ex}")
        raise

    if user is None and missing_user_error:
        raise HTTPException(HTTP_404_NOT_FOUND, "User not found.")

    return user


async def get_user(user_id: PydanticObjectId) -> UserBase:
    """Fetches and returns a user from the database, if user exists, given the user ID."""

    # fetch user and narrow its type to prevent type errors
    user_record = await get_user_from_database(user_id)
    user_record = cast(User, user_record)

    user = UserBase(
        id=user_record.id,
        name=user_record.name,
        email=user_record.email,
        date_created=user_record.date_created,
        date_updated=user_record.date_updated,
    )
    return user


async def update_user(user_id: PydanticObjectId, user_input: UserUpdateInput) -> None:
    """Updates a user in the database, if the user exists, given the user ID."""

    # fetch user and narrow its type to prevent type errors
    user = await get_user_from_database(user_id)
    user = cast(User, user)

    user.name = user_input.name
    user.email = user_input.email

    try:
        await user.replace()
    except Exception as ex:
        logger.error(f"error updating user details: {ex}")
        raise


async def delete_user(user_id: PydanticObjectId) -> None:
    """Deletes a user from the database, if the user exists, given the user ID."""

    # fetch user and narrow its type to prevent type errors
    user = await get_user_from_database(user_id)
    user = cast(User, user)

    try:
        await user.delete()
    except Exception as ex:
        logger.error(f"error deleting user: {ex}")
        raise
