from fastapi import APIRouter, Path
from loguru import logger

from src.schemas.http import users as http
from src.schemas.responses import AppResponse, BaseResponse
from src.schemas.users import UserInput, UserUpdateInput
from src.services import users as service


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", responses=http.CREATE_USER_RESPONSES)
async def create_user(user_input: UserInput):
    """Creates a user in the database and returns the user's ID."""

    logger.info("creating new user")
    user_id = await service.create_user(user_input)

    # convert to string to avoid json serialization error
    data = {"user_id": str(user_id)}
    return AppResponse(BaseResponse(data=data))


@router.get("/", responses=http.GET_USERS_RESPONSES)
async def get_all_users():
    """Gets a list of all users from the database."""

    logger.info("fetching all users")
    users = await service.get_users()

    return AppResponse(BaseResponse(data=users, key="users"), use_dict=True)


@router.get("/{user_id}", responses=http.GET_USER_RESPONSES)
async def get_user(user_id: str = Path(..., title="user_id", min_length=24, max_length=24)):
    """Fetches a single user from the databse, if the user exists."""

    logger.info(f"fetching user with id: {user_id}")
    user = await service.get_user(user_id)

    return AppResponse(BaseResponse(data=user))


@router.put("/{user_id}", status_code=204)
async def update_user(user_input: UserUpdateInput, user_id: str = Path(..., min_length=24, max_length=24)):
    """Updates a single user in the database, if the user exists."""

    logger.info(f"updating user with id: {user_id}")
    await service.update_user(user_id, user_input)
