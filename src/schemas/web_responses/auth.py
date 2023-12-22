from typing import Any, Dict

from src.schemas.web_responses.common import COMMON_RESPONSES


LOGIN_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    **COMMON_RESPONSES,
    200: {
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MDMyMzI2NTEsInN1YiI6IjY1ODUzMTI5NzljYjlmNTRlZjU5NjI0ZSJ9.qYSSRKVV4Tqwebri9pIv2HxB096eWV31l3-I-uTizxc",
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
