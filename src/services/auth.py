from beanie import PydanticObjectId
import bson.errors
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status
from src.models.users import User

from src.utils.auth_utils import compare_values
from src.services import users as users_service


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
