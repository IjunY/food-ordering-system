from fastapi import FastAPI

from app.core.config import get_settings


def create_app() -> FastAPI:
    get_settings()
    app = FastAPI(title="NTHU Meal Ordering", version="0.1.0")

    return app


app = create_app()
