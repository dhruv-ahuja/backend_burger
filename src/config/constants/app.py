from typing import Literal
from uuid import uuid4
import datetime as dt

from beanie.odm.interfaces.find import FindType, DocumentProjectionType
from beanie.odm.queries.find import FindMany, FindOne


PROJECT_NAME = "backend_burger"
S3_BUCKET_NAME = "backend-burger"
S3_FOLDER_NAME = "logs"
LOG_GROUP_NAME = "backend_burger_logs"

UNIQUE_APP_ID = uuid4().hex[:10]

PASSWORD_REGEX = r"^(?=.*[!@#$%^&*()_+{}\[\]:;<>,.?~\\/\-])(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?!.*\s).{8,}$"

INTERNAL_SCHEMA_MODELS = ["BaseResponse", "BaseError"]

ACCESS_TOKEN_DURATION = dt.timedelta(minutes=60)
REFRESH_TOKEN_DURATION = dt.timedelta(days=15)

USER_CACHE_KEY = "users"
SINGLE_USER_CACHE_DURATION = 60 * 60
USERS_CACHE_DURATION = 5 * 60


ITEMS_PER_PAGE = 100
MAXIMUM_ITEMS_PER_PAGE = 500
