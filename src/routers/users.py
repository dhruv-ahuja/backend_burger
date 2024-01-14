from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Request
from loguru import logger
from redis.asyncio import Redis
from starlette import status

from src import dependencies as deps
from src.config.constants import app
from src.models.users import User
from src.schemas.web_responses import users as resp
from src.schemas.responses import AppResponse, BaseResponse
from src.schemas.users import UserInput, UserUpdateInput
from src.services import users as service
from src.utils.services import serialize_response


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", responses=resp.CREATE_USER_RESPONSES)
async def create_user(request: Request, user_input: UserInput):
    """Creates a user in the database and returns the user's ID."""

    logger.info("creating new user")
    user_base = await service.create_user(user_input)

    redis_client: Redis = request.app.state.redis
    redis_key = f"{app.USER_CACHE_KEY}:{user_base.id}"

    serialized_user = serialize_response(BaseResponse(data=user_base))
    await redis_client.set(redis_key, serialized_user, ex=app.SINGLE_USER_CACHE_DURATION)

    # convert to string to avoid json serialization error
    data = {"user_id": str(user_base.id)}
    return BaseResponse(data=data)


@router.get("/", responses=resp.GET_USERS_RESPONSES)
async def get_all_users(request: Request, _=Depends(deps.check_access_token)):
    """Gets a list of all users from the database."""

    logger.info("fetching all users")

    redis_client: Redis = request.app.state.redis
    redis_key = app.USER_CACHE_KEY

    serialized_users = await redis_client.get(redis_key)

    if serialized_users is None:
        users = await service.get_users()

        serialized_users = serialize_response(BaseResponse(data=users, key="users"))
        await redis_client.set(redis_key, serialized_users, ex=app.USERS_CACHE_DURATION)

    return AppResponse(serialized_users)


@router.get("/{user_id}", responses=resp.GET_USER_RESPONSES)
async def get_user(request: Request, user_id: PydanticObjectId, _=Depends(deps.check_access_token)):
    """Fetches a single user from the database, if the user exists."""

    logger.info(f"fetching user with id: {user_id}")

    redis_client: Redis = request.app.state.redis
    redis_key = f"{app.USER_CACHE_KEY}:{user_id}"

    serialized_user = await redis_client.get(redis_key)

    if serialized_user is None:
        user_base = await service.get_user(user_id)

        serialized_user = serialize_response(BaseResponse(data=user_base))
        await redis_client.set(redis_key, serialized_user, ex=app.SINGLE_USER_CACHE_DURATION)

    return AppResponse(serialized_user)


@router.put("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, responses=resp.UPDATE_USER_RESPONSES)
async def update_user(
    request: Request,
    user_input: UserUpdateInput,
    user_id: PydanticObjectId,
    user: User = Depends(deps.get_current_user),
) -> None:
    """Updates a single user in the database, if the user exists."""

    await deps.check_access_to_user_resource(user_id, user)

    logger.info(f"updating user with id: {user_id}")
    user_base = await service.update_user(user_id, user_input)

    redis_client: Redis = request.app.state.redis
    redis_key = f"{app.USER_CACHE_KEY}:{user_id}"

    # create, serialize and cache single user response object
    serialized_user = serialize_response(BaseResponse(data=user_base))
    await redis_client.set(redis_key, serialized_user, ex=app.SINGLE_USER_CACHE_DURATION)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, responses=resp.DELETE_USER_RESPONSES)
async def delete_user(request: Request, user_id: PydanticObjectId, user: User = Depends(deps.get_current_user)) -> None:
    """Deletes a single user from the database, if the user exists."""

    await deps.check_access_to_user_resource(user_id, user)

    logger.info(f"deleting user with id: {user_id}")
    await service.delete_user(user_id)

    redis_client: Redis = request.app.state.redis
    redis_key = f"{app.USER_CACHE_KEY}:{user_id}"

    await redis_client.delete(redis_key)
