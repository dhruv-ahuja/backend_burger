import os


# Set before test modules import application settings. Explicitly configured test
# environments, such as CI, can still supply their own MongoDB URL.
os.environ.setdefault(
    "DB_URL",
    "mongodb://localhost:27017/backendBurgerTest?replicaSet=rs0&directConnection=true",
)
