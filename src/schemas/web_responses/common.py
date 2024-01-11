COMMON_RESPONSES = {
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
    404: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {"type": "resource_not_found", "message": "Not Found", "fields": None},
                }
            }
        }
    },
    405: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {"type": "method_not_allowed", "message": "Method not allowed.", "fields": None},
                }
            }
        }
    },
    500: {
        "content": {
            "application/json": {
                "example": {
                    "data": None,
                    "error": {
                        "type": "unknown_error",
                        "message": "An unknown error occured. Please try again later.",
                        "fields": None,
                    },
                }
            }
        }
    },
}
