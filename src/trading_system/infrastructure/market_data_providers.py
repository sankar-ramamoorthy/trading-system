"""Provider selection for read-only market data imports."""

from dataclasses import dataclass
from datetime import date

from trading_system.infrastructure.alpaca.market_data_source import (
    AlpacaDailyOHLCVImportSource,
)
from trading_system.infrastructure.alpaca.options_chain_source import (
    AlpacaOptionsChainImportSource,
)
from trading_system.infrastructure.massive.market_data_source import (
    MassiveDailyOHLCVImportSource,
)
from trading_system.infrastructure.massive.options_chain_source import (
    MassiveOptionsChainImportSource,
)
from trading_system.infrastructure.yfinance.market_data_source import (
    YFinanceDailyOHLCVImportSource,
)
from trading_system.infrastructure.yfinance.options_chain_source import (
    YFinanceOptionsChainImportSource,
)
from trading_system.ports.market_context import MarketContextImportSource


@dataclass(frozen=True)
class MarketDataImportSourceSelection:
    """Resolved source adapter and metadata for one provider-backed import."""

    source_adapter: MarketContextImportSource
    source: str
    source_ref: str


class MarketDataProviderRegistry:
    """Creates provider-backed market data import sources."""

    def create_daily_ohlcv_source(
        self,
        *,
        provider: str,
        symbol: str,
        start: date,
        end: date,
    ) -> MarketDataImportSourceSelection:
        """Return a daily OHLCV import source for a supported provider."""
        provider_name = provider.strip().lower()
        if provider_name == "yfinance":
            source_adapter = YFinanceDailyOHLCVImportSource(symbol, start, end)
            return MarketDataImportSourceSelection(
                source_adapter=source_adapter,
                source="yfinance",
                source_ref=source_adapter.source_ref,
            )
        if provider_name == "massive":
            source_adapter = MassiveDailyOHLCVImportSource(symbol, start, end)
            return MarketDataImportSourceSelection(
                source_adapter=source_adapter,
                source="massive",
                source_ref=source_adapter.source_ref,
            )
        if provider_name == "alpaca":
            source_adapter = AlpacaDailyOHLCVImportSource(symbol, start, end)
            return MarketDataImportSourceSelection(
                source_adapter=source_adapter,
                source="alpaca",
                source_ref=source_adapter.source_ref,
            )
        raise ValueError("Market data provider is not supported.")

    def create_options_chain_source(
        self,
        *,
        provider: str,
        symbol: str,
        expiration: date,
    ) -> "MarketDataImportSourceSelection":
        """Return an options chain import source for a supported provider."""
        provider_name = provider.strip().lower()
        if provider_name == "yfinance":
            source_adapter = YFinanceOptionsChainImportSource(symbol, expiration)
            return MarketDataImportSourceSelection(
                source_adapter=source_adapter,
                source="yfinance",
                source_ref=source_adapter.source_ref,
            )
        if provider_name == "massive":
            source_adapter = MassiveOptionsChainImportSource(symbol, expiration)
            return MarketDataImportSourceSelection(
                source_adapter=source_adapter,
                source="massive",
                source_ref=source_adapter.source_ref,
            )
        if provider_name == "alpaca":
            source_adapter = AlpacaOptionsChainImportSource(symbol, expiration)
            return MarketDataImportSourceSelection(
                source_adapter=source_adapter,
                source="alpaca",
                source_ref=source_adapter.source_ref,
            )
        raise ValueError("Options chain provider is not supported.")
