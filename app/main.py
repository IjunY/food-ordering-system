from fastapi import FastAPI

from app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = get_settings()
    app = FastAPI(title="Food Ordering System", version="0.1.0")

    app.state.app_settings = settings

    return app
