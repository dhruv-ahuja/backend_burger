from typing import Literal
from uuid import uuid4
import datetime as dt
import operator

from beanie.odm.interfaces.find import FindType, DocumentProjectionType
from beanie.odm.operators.find.evaluation import RegEx as RegExOperator
from beanie.odm.queries.find import FindMany


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

SORT_OPERATION = Literal["asc", "desc"]
FIND_MANY_QUERY = FindMany[FindType] | FindMany[DocumentProjectionType]

FILTER_OPERATION = Literal["=", "!=", ">", ">=", "<", "<=", "like"]
FILTER_OPERATION_MAP = {
    "=": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "like": RegExOperator,
}
NESTED_FILTER_OPERATION_MAP = {
    "=": "$eq",
    ">": "$gt",
    ">=": "$gte",
    "<": "$lt",
    "<=": "$lte",
}
