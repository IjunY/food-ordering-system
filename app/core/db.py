from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.config import Settings


# The parent class of every schema
# Uses naming convention to prevent random naming by Alembic
class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",  # ck_order_items_quantity_positive
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


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
