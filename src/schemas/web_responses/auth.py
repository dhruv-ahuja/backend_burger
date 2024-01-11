from typing import Any

from src.schemas.web_responses.common import COMMON_RESPONSES
from src.schemas.web_responses.users import USER_NOT_FOUND_RESPONSE


# TODO: add 400 responses
LOGIN_RESPONSES: dict[int | str, dict[str, Any]] = {
    **COMMON_RESPONSES,
    200: {
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "access_token": "<ACCESS_TOKEN>",
                        "refresh_token": "<REFRESH_TOKEN>",
                        "type": "Bearer",
                    },
                    "error": None,
                }
            }
        }
    },
    400: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {"type": "invalid_input", "message": "invalid username", "fields": None},
                },
            }
        }
    },
    404: {"content": {"application/json": {"example": USER_NOT_FOUND_RESPONSE}}},
    422: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {
                        "type": "validation_error",
                        "message": "Input failed validation.",
                        "fields": [
                            {"error_type": "missing", "field": "username"},
                            {"error_type": "missing", "field": "password"},
                        ],
                    },
                }
            }
        }
    },
}
LOGIN_RESPONSES.pop(403)


LOGOUT_RESPONSES: dict[int | str, dict[str, Any]] = {**COMMON_RESPONSES}


TOKEN_RESPONSES: dict[int | str, dict[str, Any]] = {
    **COMMON_RESPONSES,
    200: {
        "content": {
            "application/json": {
                "example": {
                    "data": {"access_token": "<ACCESS_TOKEN>", "type": "Bearer"},
                    "error": None,
                }
            }
        }
    },
    422: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {
                        "type": "validation_error",
                        "message": "Input failed validation.",
                        "fields": [{"error_type": "missing", "field": "refresh_token"}],
                    },
                }
            }
        }
    },
}
