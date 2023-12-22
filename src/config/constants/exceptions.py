from typing import NamedTuple


class Error(NamedTuple):
    """Error encapsulates an error's response code and response message."""

    type_: str
    message: str


ERROR_MAPPING = {
    400: Error("invalid_input", "Input is invalid."),
    401: Error("invalid_credentials", "Invalid credentials entered."),
    403: Error("insufficient_permission", "Insufficient permission to access resource."),
    404: Error("resource_not_found", "Resource not found."),
    405: Error("method_not_allowed", "Method not allowed."),
    422: Error("validation_error", "Input failed validation."),
    500: Error("unknown_error", "An unknown error occured. Please try again later."),
}
