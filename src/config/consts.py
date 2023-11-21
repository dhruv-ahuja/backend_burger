import os


LOG_DIRECTORY = os.path.expanduser("~/log/backendBurger")

LOGGER_FILENAME_FORMAT = "backendBurger_{time:DD-MM-YYYY}.log"

LOGGER_MESSAGE_FORMAT = "{time:DD-MM-YYYY HH:mm:ss} | {level} | {name}:{function}:{line} | {message} | context: {extra}"

PROJECT_NAME = "backendBurger"
