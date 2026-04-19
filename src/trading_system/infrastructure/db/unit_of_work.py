"""SQLAlchemy unit of work implementation skeleton."""

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker


class SqlAlchemyUnitOfWork:
    """Transaction boundary backed by a SQLAlchemy session."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self.session = self._session_factory()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.session is None:
            return
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.session.close()

    def commit(self) -> None:
        """Commit pending database changes."""
        if self.session is None:
            raise RuntimeError("Unit of work has not been entered.")
        self.session.commit()

    def rollback(self) -> None:
        """Rollback pending database changes."""
        if self.session is None:
            raise RuntimeError("Unit of work has not been entered.")
        self.session.rollback()
