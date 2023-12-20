from passlib.hash import argon2


def hash_value(value: str) -> str:
    """Hashes the given value."""

    return argon2.hash(value)


def compare_values(value: str, hashed_value: str) -> bool:
    """Compares a plain-text value with a hashed value and confirms whether they are same."""

    return argon2.verify(value, hashed_value)
