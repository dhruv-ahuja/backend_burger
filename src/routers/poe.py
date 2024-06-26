from fastapi import APIRouter, Depends, Query

from src import dependencies as deps
from src.schemas.web_responses import users as resp
from src.schemas.responses import AppResponse, BaseResponse
from src.services import poe as service


router = APIRouter(prefix="/poe", tags=["Path of Exile"])


# TODO: add responses
@router.get("/categories", responses=resp.GET_USERS_RESPONSES)
async def get_all_users(_=Depends(deps.check_access_token)):
    """Gets a list of all item categories from the database, mapped by their group names."""

    item_categories = await service.get_item_categories()
    item_category_mapping = service.group_item_categories(item_categories)

    return AppResponse(BaseResponse(data=item_category_mapping))
