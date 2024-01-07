from uuid import uuid4

PROJECT_NAME = "backend_burger"

S3_BUCKET_NAME = "backend-burger"

S3_FOLDER_NAME = "logs"

UNIQUE_APP_ID = uuid4().hex[:10]

PASSWORD_REGEX = r"^(?=.*[!@#$%^&*()_+{}\[\]:;<>,.?~\\/\-])(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?!.*\s).{8,}$"

INTERNAL_SCHEMA_MODELS = ["BaseResponse", "BaseError"]
