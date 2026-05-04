"""Tests for the Alpaca daily OHLCV snapshot source adapter."""

from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from trading_system.infrastructure.alpaca.market_data_source import (
    AlpacaDailyOHLCVImportSource,
)
from trading_system.infrastructure.local_secret_vault import LocalSecretVaultError


def test_load_daily_ohlcv_payload_from_provider_result() -> None:
    """The adapter converts Alpaca bars into a stable snapshot payload."""
    client = _StockClient(
        {
            "AAPL": [
                SimpleNamespace(
                    timestamp=datetime(2026, 4, 1, tzinfo=UTC),
                    open=100.0,
                    high=105.0,
                    low=99.5,
                    close=104.0,
                    volume=1000,
                    vwap=102.5,
                    trade_count=42,
                ),
                SimpleNamespace(
                    timestamp=datetime(2026, 4, 2, tzinfo=UTC),
                    open=104.0,
                    high=106.0,
                    low=101.0,
                    close=105.5,
                    volume=1200,
                ),
            ]
        }
    )

    source = AlpacaDailyOHLCVImportSource(
        "aapl",
        date(2026, 4, 1),
        date(2026, 4, 3),
        stock_client=client,
    )
    imported = source.load()

    assert imported.context_type == "daily_ohlcv"
    assert imported.observed_at.isoformat() == "2026-04-02T00:00:00+00:00"
    assert imported.payload == {
        "symbol": "AAPL",
        "provider": "alpaca",
        "interval": "1d",
        "feed": "iex",
        "adjustment": "raw",
        "start": "2026-04-01",
        "end": "2026-04-03",
        "bars": [
            {
                "date": "2026-04-01",
                "open": 100.0,
                "high": 105.0,
                "low": 99.5,
                "close": 104.0,
                "volume": 1000,
                "vwap": 102.5,
                "trade_count": 42,
            },
            {
                "date": "2026-04-02",
                "open": 104.0,
                "high": 106.0,
                "low": 101.0,
                "close": 105.5,
                "volume": 1200,
            },
        ],
    }


def test_load_daily_ohlcv_uses_expected_client_call() -> None:
    """The adapter calls Alpaca stock bars with the free-tier feed shape."""
    client = _StockClient(
        {"AAPL": [{"t": "2026-04-01T00:00:00Z", "o": 1, "h": 2, "l": 1, "c": 2, "v": 100}]}
    )

    source = AlpacaDailyOHLCVImportSource(
        "AAPL",
        date(2026, 4, 1),
        date(2026, 4, 3),
        stock_client=client,
    )
    source.load()

    request = client.requests[0]
    assert request.symbol_or_symbols == "AAPL"
    assert request.start.isoformat() == "2026-04-01T00:00:00"
    assert request.end.isoformat() == "2026-04-03T00:00:00"
    assert str(request.timeframe) == "1Day"
    assert request.feed.value == "iex"
    assert request.adjustment.value == "raw"


def test_load_daily_ohlcv_requires_api_key(monkeypatch, tmp_path) -> None:
    """Alpaca-backed imports require the reserved Alpaca credentials."""
    import trading_system.infrastructure.local_secret_vault as secret_vault

    monkeypatch.setattr(secret_vault, "DEFAULT_VAULT_PATH", tmp_path / "keys.enc")
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)

    source = AlpacaDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))

    with pytest.raises(LocalSecretVaultError, match="ALPACA_API_KEY is required"):
        source.load()


def test_load_daily_ohlcv_rejects_empty_result() -> None:
    """The adapter fails clearly when Alpaca returns no bars."""
    source = AlpacaDailyOHLCVImportSource(
        "AAPL",
        date(2026, 4, 1),
        date(2026, 4, 3),
        stock_client=_StockClient({"AAPL": []}),
    )

    with pytest.raises(ValueError, match="No daily OHLCV data returned"):
        source.load()


def test_load_daily_ohlcv_wraps_provider_failure() -> None:
    """Provider errors are reported without leaking API key material."""
    source = AlpacaDailyOHLCVImportSource(
        "AAPL",
        date(2026, 4, 1),
        date(2026, 4, 3),
        stock_client=_FailingStockClient(),
    )

    with pytest.raises(ValueError, match="Alpaca daily bars fetch failed for AAPL"):
        source.load()


def test_load_daily_ohlcv_rejects_invalid_date_range() -> None:
    """The adapter guards its own date window boundary."""
    with pytest.raises(ValueError, match="End date must be after start date"):
        AlpacaDailyOHLCVImportSource("AAPL", date(2026, 4, 3), date(2026, 4, 3))


class _StockClient:
    def __init__(self, data):
        self._data = data
        self.requests = []

    def get_stock_bars(self, request):
        self.requests.append(request)
        return SimpleNamespace(data=self._data)


class _FailingStockClient:
    def get_stock_bars(self, request):
        raise RuntimeError("rate limit")
