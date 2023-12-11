import os


LOGS_DIRECTORY = os.path.expanduser("~/log/backend_burger")

LOGS_DATETIME_FORMAT = "%d-%m-%Y"

LOGGER_FILENAME_FORMAT = "backend_burger_{time:DD-MM-YYYY}.log"

LOGGER_MESSAGE_FORMAT = "{time:DD-MM-YYYY HH:mm:ss} | {level} | {name}:{function}:{line} | {message} | context: {extra}"

S3_LOGS_UPLOAD_COUNT = 7
"""Number of log files to upload to S3."""
