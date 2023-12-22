from beanie import PydanticObjectId
from beanie.operators import Set
import bson.errors
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


async def get_user(user_id: str) -> UserBase:
    """Fetches and returns a user from the database, if user exists, given the user ID."""

    try:
        id_ = PydanticObjectId(user_id)
        user_record = await User.get(id_)
    except bson.errors.InvalidId:
        logger.error("received invalid user_id")
        raise HTTPException(HTTP_400_BAD_REQUEST, "Invalid user_id.")
    except Exception as ex:
        logger.error(f"error fetching user: {ex}")
        raise

    if user_record is None:
        raise HTTPException(HTTP_404_NOT_FOUND, "User not found.")

    user = UserBase(
        id=user_record.id,
        name=user_record.name,
        email=user_record.email,
        date_created=user_record.date_created,
        date_updated=user_record.date_updated,
    )
    return user


async def update_user(user_id: str, user_input: UserUpdateInput) -> None:
    """Updates a user in the database, if the user exists, given the user ID."""

    try:
        id_ = PydanticObjectId(user_id)
        user = await User.get(id_)
    except bson.errors.InvalidId:
        logger.error("received invalid user_id")
        raise HTTPException(HTTP_400_BAD_REQUEST, "Invalid user_id.")
    except Exception as ex:
        logger.error(f"error fetching user for update: {ex}")
        raise

    if user is None:
        raise HTTPException(HTTP_404_NOT_FOUND, "User not found.")

    user.name = user_input.name
    user.email = user_input.email

    try:
        await user.replace()
    except Exception as ex:
        logger.error(f"error updating user details: {ex}")


async def delete_user(user_id: str) -> None:
    """Deletes a user from the database, if the user exists, given the user ID."""

    try:
        id_ = PydanticObjectId(user_id)
        user = await User.get(id_)
    except bson.errors.InvalidId:
        logger.error("received invalid user_id")
        raise HTTPException(HTTP_400_BAD_REQUEST, "Invalid user_id.")
    except Exception as ex:
        logger.error(f"error fetching user: {ex}")
        raise

    if user is None:
        raise HTTPException(HTTP_404_NOT_FOUND, "User not found.")

    try:
        await user.delete()
    except Exception as ex:
        logger.error(f"error deleting user: {ex}")
        raise
