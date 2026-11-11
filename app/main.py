from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.db import get_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    # If not a test (settings == None) - get settings from .env
    if settings is None:
        settings = get_settings()
    app = FastAPI(title="Food Ordering System", version="0.1.0")

    app.state.app_settings = settings

    # creates the session factory at startup
    app.state.session_factory = sessionmaker(
        bind=get_engine(settings), expire_on_commit=False
    )

    return app
