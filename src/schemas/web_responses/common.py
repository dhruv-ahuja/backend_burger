COMMON_RESPONSES = {
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
