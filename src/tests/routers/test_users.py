from httpx import AsyncClient
import pytest

from src import main
from src.models.users import User
from src.schemas.users import UserBase


@pytest.mark.asyncio
async def test_create_user():
    """Tests creating a user with the positive flow."""

    user_input = {"name": "test_user", "email": "test_user_email@email.co.io", "password": "TestUserBurger!1"}

    async with AsyncClient(app=main.app, base_url="http://test") as client:
        response = await client.post("/users/", json=user_input)

    assert response.status_code == 201

    # perform cleanup
    await User.find_one(User.email == user_input["email"]).delete()


@pytest.mark.asyncio
async def test_create_user_wrong_input():
    """Tests creating a user with the wrong input."""

    user_input = {"name": "test_user", "email": "test_user_email@email.co@in", "password": "test"}

    error_value = {
        "data": None,
        "error": {
            "type": "validation_error",
            "message": "Input failed validation.",
            "fields": [
                {"error_type": "value_error", "field": "email"},
                {"error_type": "too_short", "field": "password"},
            ],
        },
    }

    async with AsyncClient(app=main.app, base_url="http://test") as client:
        response = await client.post("/users/", json=user_input)

    assert response.status_code == 422
    assert response.json() == error_value


@pytest.mark.asyncio
async def test_create_duplicate_user():
    """Tests creating users with duplicate emails."""

    user_input = {"name": "test_user", "email": "test_user_email@email.co.io", "password": "TestUserBurger!1"}

    error_value = {
        "data": None,
        "error": {"type": "invalid_input", "message": "Email associated with another account.", "fields": None},
    }

    async with AsyncClient(app=main.app, base_url="http://test") as client:
        response = await client.post("/users/", json=user_input)
        assert response.status_code == 201

        error_response = response = await client.post("/users/", json=user_input)

    assert error_response.status_code == 400
    assert error_response.json() == error_value

    # perform cleanup
    await User.find_one(User.email == user_input["email"]).delete()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_user", [True], indirect=True)
@pytest.mark.parametrize("get_login_tokens", ["access"], indirect=True)
async def test_get_users(test_user, get_login_tokens):
    """Tests getting list of users from the database."""

    users: list[UserBase] = [test_user]
    headers = {"Authorization": f"Bearer {get_login_tokens}"}

    async with AsyncClient(app=main.app, base_url="http://test", headers=headers) as client:
        response = await client.get("/users/")

    assert response.status_code == 200

    response_users: list[UserBase] = response.json()["data"]["users"]
    assert len(response_users) == len(users)

    for i in range(len(users)):
        user = users[i]
        response_user = UserBase.model_validate(response_users[i])

        assert user.id == response_user.id
        assert user.name == response_user.name
        assert user.email == response_user.email
        assert user.role == response_user.role


@pytest.mark.asyncio
@pytest.mark.parametrize("test_user", [True], indirect=True)
@pytest.mark.parametrize("get_login_tokens", ["access"], indirect=True)
async def test_get_user(test_user, get_login_tokens):
    """Tests getting an existing user from the database."""

    user: UserBase = test_user
    headers = {"Authorization": f"Bearer {get_login_tokens}"}

    async with AsyncClient(app=main.app, base_url="http://test", headers=headers) as client:
        response = await client.get(f"/users/{user.id}")

    assert response.status_code == 200

    response_user = UserBase.model_validate(response.json()["data"])

    assert user.id == response_user.id
    assert user.name == response_user.name
    assert user.email == response_user.email
    assert user.role == response_user.role


# * using `test_user` prevents issues when running after `delete_user` test
@pytest.mark.asyncio
@pytest.mark.parametrize("get_login_tokens", ["access"], indirect=True)
@pytest.mark.parametrize("test_user", [False], indirect=True)
async def test_get_invalid_user(get_login_tokens, test_user):
    """Tests getting a non-existent user from the database."""

    headers = {"Authorization": f"Bearer {get_login_tokens}"}

    async with AsyncClient(app=main.app, base_url="http://test", headers=headers) as client:
        response = await client.get("/users/5eb7cf5a86d9755df1111521")

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("test_user", [True], indirect=True)
@pytest.mark.parametrize("get_login_tokens", ["access"], indirect=True)
async def test_get_current_user(test_user, get_login_tokens):
    """Tests getting current user's details from the database."""

    user: UserBase = test_user
    headers = {"Authorization": f"Bearer {get_login_tokens}"}

    async with AsyncClient(app=main.app, base_url="http://test", headers=headers) as client:
        response = await client.get("/users/current")

    assert response.status_code == 200

    response_user = UserBase.model_validate(response.json()["data"])

    assert user.id == response_user.id
    assert user.name == response_user.name
    assert user.email == response_user.email
    assert user.role == response_user.role


@pytest.mark.asyncio
@pytest.mark.parametrize("test_user", [True], indirect=True)
@pytest.mark.parametrize("get_login_tokens", ["access"], indirect=True)
async def test_update_user(test_user, get_login_tokens):
    """Tests updating a user's details."""

    user: UserBase = test_user
    headers = {"Authorization": f"Bearer {get_login_tokens}"}

    user_input = {"name": "test_user part 2", "email": "test_user_email@email.co.io"}

    async with AsyncClient(app=main.app, base_url="http://test", headers=headers) as client:
        response = await client.put(f"/users/{user.id}", json=user_input)

    assert response.status_code == 204

    updated_user = await User.get(user.id)

    assert updated_user is not None
    assert updated_user.name == user_input["name"]
    assert updated_user.email == user_input["email"]

    # perform cleanup
    await User.find_one(User.email == user_input["email"]).delete()


@pytest.mark.asyncio
@pytest.mark.parametrize("test_user", [False], indirect=True)
@pytest.mark.parametrize("get_login_tokens", ["access"], indirect=True)
async def test_delete_user(test_user, get_login_tokens):
    """Tests deleting a user from the database."""

    user: UserBase = test_user
    headers = {"Authorization": f"Bearer {get_login_tokens}"}

    async with AsyncClient(app=main.app, base_url="http://test", headers=headers) as client:
        response = await client.delete(f"/users/{user.id}")

    assert response.status_code == 204

    user_record = await User.get(user.id)

    assert user_record is None
