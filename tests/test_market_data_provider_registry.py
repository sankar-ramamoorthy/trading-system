"""Tests for read-only market data provider selection."""

from datetime import date

import pytest

from trading_system.infrastructure.market_data_providers import (
    MarketDataProviderRegistry,
)


def test_registry_resolves_yfinance_daily_ohlcv_source() -> None:
    """The registry returns yfinance source metadata for daily OHLCV imports."""
    selection = MarketDataProviderRegistry().create_daily_ohlcv_source(
        provider="YFINANCE",
        symbol="aapl",
        start=date(2026, 4, 1),
        end=date(2026, 4, 3),
    )

    assert selection.source == "yfinance"
    assert selection.source_ref == (
        "symbol=AAPL;start=2026-04-01;end=2026-04-03;"
        "interval=1d;auto_adjust=false"
    )
    assert callable(selection.source_adapter.load)


def test_registry_rejects_unsupported_provider() -> None:
    """Only explicitly supported providers can be selected."""
    with pytest.raises(ValueError, match="Market data provider is not supported"):
        MarketDataProviderRegistry().create_daily_ohlcv_source(
            provider="massive",
            symbol="AAPL",
            start=date(2026, 4, 1),
            end=date(2026, 4, 3),
        )
