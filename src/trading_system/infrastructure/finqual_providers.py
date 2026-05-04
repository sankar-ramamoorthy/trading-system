"""Provider selection for read-only Finqual context imports."""

from dataclasses import dataclass

from trading_system.infrastructure.finqual.context_sources import (
    Finqual13FImportSource,
    FinqualFinancialStatementImportSource,
    FinqualInsiderTransactionsImportSource,
)
from trading_system.ports.market_context import MarketContextImportSource


@dataclass(frozen=True)
class FinqualImportSourceSelection:
    """Resolved Finqual source adapter and metadata for one import."""

    source_adapter: MarketContextImportSource
    source: str
    source_ref: str


class FinqualProviderRegistry:
    """Creates Finqual-backed fundamentals and ownership import sources."""

    def create_financial_statement_source(
        self,
        *,
        provider: str,
        symbol: str,
        statement: str,
        start: int,
        end: int,
        quarter: bool,
    ) -> FinqualImportSourceSelection:
        """Return a financial statement import source for Finqual."""
        self._validate_provider(provider)
        source_adapter = FinqualFinancialStatementImportSource(
            symbol,
            statement,
            start,
            end,
            quarter=quarter,
        )
        return FinqualImportSourceSelection(
            source_adapter=source_adapter,
            source="finqual",
            source_ref=source_adapter.source_ref,
        )

    def create_insider_transactions_source(
        self,
        *,
        provider: str,
        symbol: str,
        period: str,
    ) -> FinqualImportSourceSelection:
        """Return an insider transactions import source for Finqual."""
        self._validate_provider(provider)
        source_adapter = FinqualInsiderTransactionsImportSource(symbol, period)
        return FinqualImportSourceSelection(
            source_adapter=source_adapter,
            source="finqual",
            source_ref=source_adapter.source_ref,
        )

    def create_13f_source(
        self,
        *,
        provider: str,
        cik: str,
        period: int,
    ) -> FinqualImportSourceSelection:
        """Return a 13F holdings import source for Finqual."""
        self._validate_provider(provider)
        source_adapter = Finqual13FImportSource(cik, period)
        return FinqualImportSourceSelection(
            source_adapter=source_adapter,
            source="finqual",
            source_ref=source_adapter.source_ref,
        )

    @staticmethod
    def _validate_provider(provider: str) -> None:
        if provider.strip().lower() != "finqual":
            raise ValueError("Finqual provider is not supported.")
