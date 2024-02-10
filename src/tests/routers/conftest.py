from beanie import PydanticObjectId
import beanie.exceptions
from httpx import AsyncClient
from pydantic import SecretStr
import pytest
import pytest_asyncio
from typing import Any, AsyncGenerator

from src.main import app
from src.models.users import User
from src.schemas.users import Role, UserBase
from src.utils.auth_utils import hash_value


ID = PydanticObjectId("65b7d879479209d338da86b6")
EMAIL = "test_user_email@email.co.io"
PASSWORD = "backendBurger123!"


@pytest_asyncio.fixture(scope="module", autouse=True)
async def delete_test_user():
    """Deletes the test user from the database, if it already exists. This prevents any potential 'duplicate user'
    errors during the tests."""

    await User.find_one(User.email == EMAIL).delete()


# TODO: Create test client object fixture
# TODO: break this down into separate functions to avoid re-running user.save()
@pytest_asyncio.fixture(scope="module")
async def test_user(request: pytest.FixtureRequest) -> AsyncGenerator[User | UserBase, Any]:
    """Creates a test user object, deleting it post-usage."""

    hashed_password = hash_value(PASSWORD)

    user = User(
        id=ID,
        name="backend_burger_test",
        email=EMAIL,
        role=Role.admin,
        password=SecretStr(hashed_password),
    )

    # workaround for the duplicate user object creation error
    try:
        await user.save()  # type: ignore
    except (beanie.exceptions.RevisionIdWasChanged, beanie.exceptions.DocumentAlreadyCreated):
        pass

    yield_user_base = getattr(request, "param", None)
    if yield_user_base:
        user_base = UserBase(
            id=user.id,
            name="backend_burger_test",
            email=EMAIL,
            role=Role.admin,
            created_time=user.created_time,
            updated_time=user.updated_time,
        )

        yield user_base
    else:
        yield user

    await user.delete()  # type: ignore


@pytest_asyncio.fixture
async def get_login_tokens(request: pytest.FixtureRequest, test_user):
    """Logs the test user into the application, getting the access and refresh tokens as response.
    Returns the desired token type."""

    token_type = request.param
    form_data = {"username": EMAIL, "password": PASSWORD}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/auth/login", data=form_data)

    assert response.status_code == 200

    data: dict[str, str] = response.json()["data"]

    if token_type == "access":
        yield data["access_token"]
    elif token_type == "refresh":
        yield data["refresh_token"]
    else:
        yield data
