from collections.abc import Iterator
from functools import lru_cache
from sqlalchemy import create_engine, Engine
from sqlalchemy.engine import make_url, URL
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import get_settings


# The parent class of every schema
class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:

    str_url = get_settings().database_url.get_secret_value()
    db_url: URL = make_url(str_url).set(drivername="postgresql+psycopg")

    # The connection between code and the database
    engine: Engine = create_engine(url=db_url, pool_pre_ping=True)
    return engine


def get_db() -> Iterator[Session]:
    engine = get_engine()

    # sessionmaker (factory) creates an instance of a session using our own settings
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    # Opens a session
    with SessionLocal() as session:
        # Hands over the session and pause
        yield session
