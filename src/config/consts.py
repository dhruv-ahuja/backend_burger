import os


LOG_DIRECTORY = os.path.expanduser("~/log/backend_burger")

LOGGER_FILENAME_FORMAT = "backend_burger_{time:DD-MM-YYYY}.log"

LOGGER_MESSAGE_FORMAT = "{time:DD-MM-YYYY HH:mm:ss} | {level} | {name}:{function}:{line} | {message} | context: {extra}"

PROJECT_NAME = "backend_burger"
