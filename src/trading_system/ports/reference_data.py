"""Reference-data lookup ports for user-facing trade capture workflows."""

from typing import Protocol

from trading_system.domain.trading.instrument import Instrument
from trading_system.domain.trading.playbook import Playbook


class ReferenceDataRepository(Protocol):
    """Read-only reference data needed by user-facing workflows."""

    def list_instruments(self) -> list[Instrument]:
        """Return known instruments."""
        ...

    def get_instrument_by_symbol(self, symbol: str) -> Instrument | None:
        """Return one instrument by symbol."""
        ...

    def list_playbooks(self) -> list[Playbook]:
        """Return known playbooks."""
        ...

    def get_playbook_by_slug(self, slug: str) -> Playbook | None:
        """Return one playbook by slug."""
        ...
