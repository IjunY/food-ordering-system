from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from app.auth.router import router as auth_router
from app.core.config import Settings, get_settings
from app.core.db import get_engine
from app.core.errors import AppError


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

    # Errors raised by the service layer -> {"detail": "..."} with the matching status code
    @app.exception_handler(AppError)
    def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail}, headers=headers
        )

    # Every endpoint lives under /api
    app.include_router(auth_router, prefix="/api")

    return app
