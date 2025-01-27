import datetime as dt
from typing import Any, Tuple

from jose import jwt, JWTError
from passlib.hash import argon2

from src.config.services import settings


def hash_value(value: str) -> str:
    """Hashes the given value."""

    return argon2.hash(value)


def compare_values(value: str, hashed_value: str) -> bool:
    """Compares a plain-text value with a hashed value and confirms whether they are same."""

    return argon2.verify(value, hashed_value)


def create_bearer_token(expiry_time: dt.timedelta, sub: str | None = None) -> Tuple[str, dt.datetime]:
    """Creates an encoded access or refresh token with the given sub and expiry time."""

    token_expires_in = dt.datetime.now(dt.UTC) + expiry_time
    token_data: dict[str, Any] = {"exp": token_expires_in}

    if sub is not None:
        token_data["sub"] = sub

    jwt_secret_key = settings.jwt_secret_key.get_secret_value()
    bearer_token = jwt.encode(token_data, jwt_secret_key)

    return bearer_token, token_expires_in


def parse_bearer_token(token: str) -> dict[str, Any]:
    """Parses the given bearer token, raising an error if its invalid, and returns its data if valid."""

    jwt_secret_key = settings.jwt_secret_key.get_secret_value()

    try:
        data = jwt.decode(token, jwt_secret_key)
    except JWTError:
        raise

    return data
