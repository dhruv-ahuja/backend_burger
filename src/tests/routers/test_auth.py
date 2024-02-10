from httpx import AsyncClient
import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("get_login_tokens", ["access"], indirect=True)
async def test_logout(get_login_tokens, test_client: AsyncClient):
    """Tests logging the user out of the application."""

    headers = {"Authorization": f"Bearer {get_login_tokens}"}
    test_client.headers = headers

    response = await test_client.get("/auth/logout")
    assert response.status_code == 204

    user_response = await test_client.get("/users/current")
    assert user_response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("get_login_tokens", [None], indirect=True)
async def test_token_refresh(get_login_tokens: dict[str, str], test_client: AsyncClient):
    """Tests refreshing access token for the user."""

    access_token = get_login_tokens["access_token"]
    refresh_token = get_login_tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    test_client.headers = headers

    input_data = {"refresh_token": refresh_token}

    response = await test_client.post("/auth/token", json=input_data)
    assert response.status_code == 200

    token_data = response.json()["data"]
    assert token_data["type"] == "Bearer"

    new_access_token = token_data["access_token"]
    new_headers = {"Authorization": f"Bearer {new_access_token}"}

    # use new token to test logout endpoint
    test_client.headers = new_headers

    logout_response = await test_client.get("/auth/logout")
    assert logout_response.status_code == 204
