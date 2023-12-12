from fastapi import APIRouter
from loguru import logger

from src.schemas.responses import AppResponse, BaseResponse
from src.schemas.users import UserInput
from src.services import users as service


router = APIRouter(prefix="/users", tags=["Users"])


# TODO: define response examples


@router.post("/")
async def create_user(input: UserInput):
    """Creates a user in the database and returns the user's ID."""

    logger.info("creating new user")
    user_id = await service.create_user(input)

    return AppResponse(BaseResponse(data=str(user_id)))


@router.get("/")
async def get_all_users():
    """Gets a list of all users from the database."""

    logger.info("fetching all users")
    users = await service.get_users()

    return AppResponse(BaseResponse(data=users, key="users"), use_dict=True)


@router.get("/{user_id}")
async def get_user(user_id: str):
    """Fetches a single user from the databse, if the user exists."""

    logger.info(f"fetching user with id: {user_id}")
    user = await service.get_user(user_id)

    return AppResponse(BaseResponse(data=user))
