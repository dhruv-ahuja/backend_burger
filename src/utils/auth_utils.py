import datetime as dt
from typing import Any

from jose import jwt, JWTError
from passlib.hash import argon2

from src.config.services import settings


def hash_value(value: str) -> str:
    """Hashes the given value."""

    return argon2.hash(value)


def compare_values(value: str, hashed_value: str) -> bool:
    """Compares a plain-text value with a hashed value and confirms whether they are same."""

    return argon2.verify(value, hashed_value)


def create_access_token(sub: str | None = None, expiry_time: dt.timedelta | None = None) -> str:
    """Creates an encoded access token with the given sub and expiry time."""

    if expiry_time is None:
        expiry_time = dt.timedelta(minutes=60)

    token_expires_in = dt.datetime.utcnow() + expiry_time
    token_data: dict[str, Any] = {"exp": token_expires_in}

    if sub is not None:
        token_data["sub"] = sub

    jwt_secret_key = settings.jwt_secret_key.get_secret_value()
    access_token = jwt.encode(token_data, jwt_secret_key)

    return access_token


def parse_access_token(access_token: str) -> dict[str, Any]:
    """Parses the given access token, raising an error if its invalid, and returns its data if valid."""

    jwt_secret_key = settings.jwt_secret_key.get_secret_value()

    try:
        data = jwt.decode(access_token, jwt_secret_key)
    except JWTError:
        raise

    return data
