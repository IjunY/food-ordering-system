from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.config import Settings


# The parent class of every schema
class Base(DeclarativeBase):
    pass


def get_database_url(settings: Settings) -> URL:
    return make_url(settings.database_url.get_secret_value()).set(
        drivername="postgresql+psycopg"
    )


def get_engine(settings: Settings) -> Engine:
    # The connection between code and the database
    return create_engine(url=get_database_url(settings), pool_pre_ping=True)


def get_db(request: Request) -> Iterator[Session]:

    # create session when api endpoint is called
    with request.app.state.session_factory() as session:
        # Hands over the session and pause
        yield session
