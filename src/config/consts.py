import os
from collections import namedtuple


PROJECT_NAME = "backend_burger"
LOG_DIRECTORY = os.path.expanduser("~/log/backend_burger")

LOGGER_FILENAME_FORMAT = "backend_burger_{time:DD-MM-YYYY}.log"
LOGGER_MESSAGE_FORMAT = "{time:DD-MM-YYYY HH:mm:ss} | {level} | {name}:{function}:{line} | {message} | context: {extra}"


PASSWORD_REGEX = r"^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+])[A-Za-z\d][A-Za-z\d!@#$%^&*()_+]{7,255}$"


ERROR_MESSAGES = namedtuple("error_messages", ["type", "message"])

ERROR_MAPPING = {
    422: ERROR_MESSAGES("validation_error", "Input failed validation."),
    500: ERROR_MESSAGES("unknown_error", "An unknown error occured. Please try again later."),
}
