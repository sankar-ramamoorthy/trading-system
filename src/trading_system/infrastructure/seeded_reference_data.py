"""Seeded local reference data for early web trade-capture workflows."""

from uuid import UUID

from trading_system.domain.trading.instrument import Instrument
from trading_system.domain.trading.playbook import Playbook


SEEDED_INSTRUMENTS = (
    Instrument(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        symbol="AAPL",
        name="Apple Inc.",
    ),
    Instrument(
        id=UUID("22222222-2222-4222-8222-222222222222"),
        symbol="MSFT",
        name="Microsoft Corporation",
    ),
    Instrument(
        id=UUID("33333333-3333-4333-8333-333333333333"),
        symbol="NVDA",
        name="NVIDIA Corporation",
    ),
    Instrument(
        id=UUID("44444444-4444-4444-8444-444444444444"),
        symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
    ),
    Instrument(
        id=UUID("55555555-5555-4555-8555-555555555555"),
        symbol="QQQ",
        name="Invesco QQQ Trust",
    ),
)

SEEDED_PLAYBOOKS = (
    Playbook(
        id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        slug="pullback-to-trend",
        name="Pullback To Trend",
        description="Trend-continuation setup after a controlled pullback.",
    ),
    Playbook(
        id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        slug="breakout-continuation",
        name="Breakout Continuation",
        description="Continuation setup after price clears a defined range or level.",
    ),
    Playbook(
        id=UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        slug="failed-breakdown",
        name="Failed Breakdown",
        description="Reversal setup after sellers fail to sustain a breakdown.",
    ),
)


class SeededReferenceDataRepository:
    """Read-only reference repository backed by local seeded records."""

    def __init__(
        self,
        instruments: tuple[Instrument, ...] = SEEDED_INSTRUMENTS,
        playbooks: tuple[Playbook, ...] = SEEDED_PLAYBOOKS,
    ) -> None:
        self._instruments = tuple(instruments)
        self._playbooks = tuple(playbooks)

    def list_instruments(self) -> list[Instrument]:
        """Return known instruments sorted by symbol."""
        return sorted(self._instruments, key=lambda instrument: instrument.symbol)

    def get_instrument_by_symbol(self, symbol: str) -> Instrument | None:
        """Return one instrument by case-insensitive symbol."""
        normalized = _normalize_symbol(symbol)
        for instrument in self._instruments:
            if _normalize_symbol(instrument.symbol) == normalized:
                return instrument
        return None

    def list_playbooks(self) -> list[Playbook]:
        """Return known playbooks sorted by slug."""
        return sorted(self._playbooks, key=lambda playbook: playbook.slug)

    def get_playbook_by_slug(self, slug: str) -> Playbook | None:
        """Return one playbook by case-insensitive slug."""
        normalized = _normalize_slug(slug)
        for playbook in self._playbooks:
            if _normalize_slug(playbook.slug) == normalized:
                return playbook
        return None


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _normalize_slug(slug: str) -> str:
    return slug.strip().lower()
