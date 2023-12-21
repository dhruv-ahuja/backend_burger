from typing import Any, Dict

from src.schemas.http.common import COMMON_RESPONSES


CREATE_USER_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    200: {
        "content": {
            "application/json": {"example": {"data": {"user_id": "6577d3f0e39b709bb43e85ae"}, "error": None}},
        },
    },
    400: {
        "content": {
            "application/json": {
                "example": {
                    "error": {
                        "type": "invalid_input",
                        "message": "Email associated with another account.",
                        "fields": None,
                    },
                }
            }
        },
        "data": None,
    },
    422: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {
                        "type": "validation_error",
                        "message": "Input failed validation.",
                        "fields": [
                            {"error_type": "string_too_short", "field": "name"},
                            {"error_type": "value_error", "field": "email"},
                            {"error_type": "too_short", "field": "password"},
                        ],
                    },
                }
            }
        },
        "data": None,
    },
    **COMMON_RESPONSES,
}


GET_USERS_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "error": None,
                    "data": {
                        "users": [
                            {
                                "id": "6574342ba63e1afa0f597aa5",
                                "name": "Dhruv",
                                "email": "dhruv@gmail.com",
                                "date_created": "2023-12-09T15:02:27.333000",
                                "date_updated": "2023-12-09T15:02:27.333000",
                            },
                            {
                                "id": "65774cfebf93bd80518d42e5",
                                "name": "Dhruv 2",
                                "email": "dhruv2@1gmail.com",
                                "date_created": "2023-12-11T23:25:10.369000",
                                "date_updated": "2023-12-11T23:25:10.369000",
                            },
                        ]
                    },
                }
            },
        },
    },
    **COMMON_RESPONSES,
}

GET_USER_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    200: {
        "content": {
            "application/json": {
                "example": {
                    "data": {
                        "id": "6574342ba63e1afa0f597aa5",
                        "name": "Dhruv Ahuja",
                        "email": "dhruvahuja2k@gmail.com",
                        "date_created": "2023-12-09T15:02:27.333000",
                        "date_updated": "2023-12-09T15:02:27.333000",
                    },
                    "error": None,
                }
            },
        },
    },
    400: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {"type": "invalid_input", "message": "Invalid user_id.", "fields": None},
                },
            }
        }
    },
    404: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {"type": "resource_not_found", "message": "User not found.", "fields": None},
                },
            }
        },
        "data": None,
    },
    422: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {
                        "type": "validation_error",
                        "message": "Input failed validation.",
                        "fields": [{"error_type": "string_too_short", "field": "user_id"}],
                    },
                }
            }
        },
        "data": None,
    },
    **COMMON_RESPONSES,
}

UPDATE_USER_RESPONSES: Dict[int | str, Dict[str, Any]] = {
    400: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {"type": "invalid_input", "message": "Invalid user_id.", "fields": None},
                },
            }
        }
    },
    404: {
        "content": {
            "application/json": {
                "example": [
                    {
                        "data": None,
                        "error": {"type": "resource_not_found", "message": "User not found.", "fields": None},
                    },
                    {"data": None, "error": {"type": "invalid_input", "message": "Invalid user_id.", "fields": None}},
                ]
            }
        },
        "data": None,
    },
    422: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {
                        "type": "validation_error",
                        "message": "Input failed validation.",
                        "fields": [{"error_type": "string_too_short", "field": "user_id"}],
                    },
                }
            }
        },
        "data": None,
    },
    **COMMON_RESPONSES,
}
