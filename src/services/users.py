import datetime as dt
from typing import cast

from beanie import DeleteRules, PydanticObjectId
from fastapi import HTTPException
from loguru import logger
from pydantic import SecretStr
from pymongo.errors import DuplicateKeyError
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.models.users import User
from src.schemas.users import Role, UserBase, UserInput, UserUpdateInput
from src.utils import auth_utils


async def create_user(user_input: UserInput) -> UserBase:
    """Creates a user in the database, and returns a `UserBase` representation of the newly created `User` document
    instance."""

    hashed_password = auth_utils.hash_value(user_input.password.get_secret_value())
    user = User(name=user_input.name, email=user_input.email, password=SecretStr(hashed_password), role=Role.user)

    try:
        user: User = await user.insert()  # type: ignore
    except DuplicateKeyError:
        logger.error("error creating user: duplicate email used")
        raise HTTPException(HTTP_400_BAD_REQUEST, "Email associated with another account.")
    except Exception as exc:
        logger.error(f"error creating user: {exc}; error type: {exc.__class__}")
        raise

    return UserBase.model_construct(**user.model_dump())


async def get_users() -> list[UserBase]:
    """Fetches users from the database, returning them as a list of `UserBase` instances."""

    try:
        user_records = await User.find_all().to_list()
    except Exception as exc:
        logger.error(f"error fetching users: {exc}; error_type: {exc.__class__}")
        raise

    users = []

    # parsing User to UserBase using parse_obj to avoid `id` loss -- pydantic V2 bug
    for user_record in user_records:
        user = UserBase(
            id=user_record.id,
            name=user_record.name,
            email=user_record.email,
            role=user_record.role,
            created_time=user_record.created_time,
            updated_time=user_record.updated_time,
        )
        users.append(user)

    return users


async def get_user_from_database(
    user_id: PydanticObjectId | None, user_email: str | None = None, missing_user_error: bool = True
) -> User | None:
    """Fetches a user from the database. Raises a 404 error if the user does not exist and `missing_user_error`
    is `True`."""

    if user_id is None and user_email is None:
        raise ValueError("Invalid input. Pass either user_id or user_email.")

    try:
        if user_id is not None:
            user = await User.get(user_id, fetch_links=True)
        else:
            user = await User.find(User.email == user_email, fetch_links=True).first_or_none()  # type: ignore
    except Exception as exc:
        logger.error(f"error fetching user: {exc}")
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
        role=user_record.role,
        created_time=user_record.created_time,
        updated_time=user_record.updated_time,
    )
    return user


async def update_user(user_id: PydanticObjectId, user_input: UserUpdateInput) -> UserBase:
    """Updates a user in the database, if the user exists, given the user ID. Creates and returns a `UserBase`
    instance from the `User` document instance."""

    # fetch user and narrow its type to prevent type errors
    user = await get_user_from_database(user_id)
    user = cast(User, user)

    user.name = user_input.name
    user.email = user_input.email
    user.updated_time = dt.datetime.now()

    try:
        await user.replace()  # type: ignore
    except DuplicateKeyError:
        logger.error("error updating user: duplicate email used")
        raise HTTPException(HTTP_400_BAD_REQUEST, "Email associated with another account.")
    except Exception as exc:
        logger.error(f"error updating user details: {exc}")
        raise

    return UserBase.model_construct(**user.model_dump())


async def delete_user(user_id: PydanticObjectId) -> None:
    """Deletes a user from the database, if the user exists, given the user ID."""

    # fetch user and narrow its type to prevent type errors
    user = await get_user_from_database(user_id)
    user = cast(User, user)

    try:
        await user.delete(link_rule=DeleteRules.DELETE_LINKS)  # type: ignore
    except Exception as exc:
        logger.error(f"error deleting user: {exc}")
        raise
