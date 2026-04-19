"""SQLAlchemy session construction for Postgres persistence."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create a SQLAlchemy session factory for the configured database."""
    engine = create_engine(database_url)
    return sessionmaker(bind=engine, expire_on_commit=False)
