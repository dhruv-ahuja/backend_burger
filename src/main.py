from fastapi import FastAPI

from .config import setup_services


app = FastAPI(lifespan=setup_services)
