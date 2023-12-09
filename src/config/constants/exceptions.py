from typing import NamedTuple


class ErrorMessage(NamedTuple):
    """ErrorMessage encapsulates an error's response code and response message."""

    type_: str
    message: str


ERROR_MAPPING = {
    422: ErrorMessage("validation_error", "Input failed validation."),
    500: ErrorMessage("unknown_error", "An unknown error occured. Please try again later."),
}
