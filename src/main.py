from fastapi import FastAPI

from .config import setup_services


app = FastAPI(lifespan=setup_services)


@app.get("/")
async def get():
    """Returns a simple success message indicating that the server is up and running."""

    return {"status": "ok"}
