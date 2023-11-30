PROJECT_NAME = "backend_burger"

S3_BUCKET_NAME = "backend-burger"

S3_FOLDER_NAME = "logs"

PASSWORD_REGEX = r"^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+])[A-Za-z\d][A-Za-z\d!@#$%^&*()_+]{7,255}$"

INTERNAL_SCHEMA_MODELS = ["BaseResponse", "BaseError"]
