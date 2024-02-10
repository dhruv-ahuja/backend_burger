from beanie import PydanticObjectId
import beanie.exceptions
from httpx import AsyncClient
from pydantic import SecretStr
import pytest
import pytest_asyncio
from typing import Any, AsyncGenerator

from src import main
from src.models.users import User
from src.schemas.users import Role, UserBase
from src.utils.auth_utils import hash_value


ID = PydanticObjectId("65b7d879479209d338da86b6")
EMAIL = "test_user_email@email.co.io"
PASSWORD = "backendBurger123!"

USER_INPUT = {"name": "test_user", "email": EMAIL, "password": PASSWORD}


@pytest_asyncio.fixture(scope="module")
async def test_client():
    """Initializes and yields the Async test client to test application's endpoints."""

    async with AsyncClient(app=main.app, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def test_user() -> AsyncGenerator[User | UserBase, Any]:
    """Creates and yields a test user object, deleting it post-usage. Saves the user to DB if specified."""

    user = User(
        id=ID,
        name="backend_burger_test",
        email=EMAIL,
        role=Role.admin,
        password=SecretStr(hash_value(PASSWORD)),
    )

    # * workaround as this fixture isnt accepting parameter at initialization!
    try:
        await user.save()  # type: ignore
    except (beanie.exceptions.RevisionIdWasChanged, beanie.exceptions.DocumentAlreadyCreated):
        pass

    user_base = UserBase(
        id=user.id,
        name="backend_burger_test",
        email=EMAIL,
        role=Role.admin,
        created_time=user.created_time,
        updated_time=user.updated_time,
    )

    yield user_base
    await user.delete()  # type: ignore


@pytest_asyncio.fixture
@pytest.mark.parametrize("test_user", [True], indirect=True)
async def get_login_tokens(request: pytest.FixtureRequest, test_user: UserBase, test_client: AsyncClient):
    """Logs the test user into the application, getting the access and refresh tokens as response.
    Returns the desired token type."""

    token_type = request.param
    form_data = {"username": EMAIL, "password": PASSWORD}

    response = await test_client.post("/auth/login", data=form_data)
    assert response.status_code == 200

    data: dict[str, str] = response.json()["data"]

    if token_type == "access":
        yield data["access_token"]
    elif token_type == "refresh":
        yield data["refresh_token"]
    else:
        yield data
