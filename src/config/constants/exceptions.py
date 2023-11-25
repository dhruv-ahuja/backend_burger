from collections import namedtuple


ERROR_MESSAGES = namedtuple("error_messages", ["type", "message"])

ERROR_MAPPING = {
    422: ERROR_MESSAGES("validation_error", "Input failed validation."),
    500: ERROR_MESSAGES("unknown_error", "An unknown error occured. Please try again later."),
}
