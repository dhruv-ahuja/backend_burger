from typing import Any

from src.schemas.web_responses.common import COMMON_RESPONSES


INVALID_CREDENTIALS_RESPONSE = {
    "content": {
        "application/json": {
            "example": {
                "data": None,
                "error": {
                    "type": "invalid_credentials",
                    "message": "Invalid credentials entered.",
                    "fields": None,
                },
            }
        }
    }
}

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
    401: INVALID_CREDENTIALS_RESPONSE,
}

LOGOUT_RESPONSES: dict[int | str, dict[str, Any]] = {
    **COMMON_RESPONSES,
    401: INVALID_CREDENTIALS_RESPONSE,
    403: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {
                        "type": "insufficient_permission",
                        "message": "Insufficient permission to access resource.",
                        "fields": None,
                    },
                }
            }
        }
    },
}
