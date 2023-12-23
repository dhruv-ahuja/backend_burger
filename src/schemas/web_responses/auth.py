from typing import Any, Dict

from src.schemas.web_responses.common import COMMON_RESPONSES


LOGIN_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    **COMMON_RESPONSES,
    200: {
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "access_token": "access_token_here",
                        "type": "Bearer",
                    },
                    "error": None,
                }
            }
        }
    },
    401: {
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
    },
}
