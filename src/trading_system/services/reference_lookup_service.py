"""User-facing reference lookup workflows."""

from trading_system.domain.trading.instrument import Instrument
from trading_system.domain.trading.playbook import Playbook
from trading_system.ports.reference_data import ReferenceDataRepository


class ReferenceLookupService:
    """Resolve symbols and playbook slugs into known reference records."""

    def __init__(self, repository: ReferenceDataRepository) -> None:
        self._repository = repository

    def list_instruments(self) -> list[Instrument]:
        """Return instruments available for user-facing workflows."""
        return self._repository.list_instruments()

    def resolve_instrument(self, symbol: str) -> Instrument:
        """Resolve a user-facing symbol to a known instrument."""
        instrument = self._repository.get_instrument_by_symbol(symbol)
        if instrument is None:
            raise ValueError(f"Unknown instrument symbol: {symbol}")
        return instrument

    def list_playbooks(self) -> list[Playbook]:
        """Return playbooks available for user-facing workflows."""
        return self._repository.list_playbooks()

    def resolve_playbook(self, slug: str) -> Playbook:
        """Resolve a user-facing playbook slug to a known playbook."""
        playbook = self._repository.get_playbook_by_slug(slug)
        if playbook is None:
            raise ValueError(f"Unknown playbook slug: {slug}")
        return playbook
