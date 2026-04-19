"""Unit of work interface for transactional service workflows."""

from types import TracebackType
from typing import Protocol


class UnitOfWork(Protocol):
    """Transaction boundary used by services without infrastructure details."""

    def __enter__(self) -> "UnitOfWork":
        """Enter a transaction scope."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit a transaction scope."""
        ...

    def commit(self) -> None:
        """Commit pending changes."""
        ...

    def rollback(self) -> None:
        """Rollback pending changes."""
        ...
