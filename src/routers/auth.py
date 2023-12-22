from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from loguru import logger

from src.schemas.responses import AppResponse, BaseResponse
from src.schemas.web_responses import auth as resp
from src.services import auth as service
from src.utils import auth_utils


router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/login", responses=resp.LOGIN_RESPONSES)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Logs the user into the application, checking first whether user credentials."""

    logger.info("attempting user login")

    user = await service.check_users_credentials(form_data)
    access_token = auth_utils.create_access_token(str(user.id))

    response = BaseResponse(data={"access_token": access_token, "type": "Bearer"})
    return AppResponse(response)
