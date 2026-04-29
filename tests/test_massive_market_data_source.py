"""Tests for the Massive.com daily OHLCV snapshot source adapter."""

from datetime import date
from types import SimpleNamespace

import pytest

from trading_system.infrastructure.massive.market_data_source import (
    MassiveDailyOHLCVImportSource,
)


def test_load_daily_ohlcv_payload_from_provider_result(monkeypatch) -> None:
    """The adapter converts provider aggregates into a stable snapshot payload."""
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.market_data_source.import_module",
        lambda name: SimpleNamespace(
            RESTClient=lambda api_key: _Client(
                [
                    SimpleNamespace(
                        timestamp=1775001600000,
                        open=100.0,
                        high=105.0,
                        low=99.5,
                        close=104.0,
                        volume=1000,
                        vwap=102.5,
                        transactions=42,
                    ),
                    SimpleNamespace(
                        timestamp=1775088000000,
                        open=104.0,
                        high=106.0,
                        low=101.0,
                        close=105.5,
                        volume=1200,
                    ),
                ]
            )
        ),
    )

    source = MassiveDailyOHLCVImportSource("aapl", date(2026, 4, 1), date(2026, 4, 3))
    imported = source.load()

    assert imported.context_type == "daily_ohlcv"
    assert imported.observed_at.isoformat() == "2026-04-02T00:00:00+00:00"
    assert imported.payload["symbol"] == "AAPL"
    assert imported.payload["provider"] == "massive"
    assert imported.payload["interval"] == "1d"
    assert imported.payload["timespan"] == "day"
    assert imported.payload["start"] == "2026-04-01"
    assert imported.payload["end"] == "2026-04-03"
    assert imported.payload["adjusted"] is False
    assert imported.payload["bars"] == [
        {
            "date": "2026-04-01",
            "open": 100.0,
            "high": 105.0,
            "low": 99.5,
            "close": 104.0,
            "volume": 1000,
            "vwap": 102.5,
            "transactions": 42,
        },
        {
            "date": "2026-04-02",
            "open": 104.0,
            "high": 106.0,
            "low": 101.0,
            "close": 105.5,
            "volume": 1200,
        },
    ]


def test_load_daily_ohlcv_uses_expected_client_call(monkeypatch) -> None:
    """The adapter calls the narrow Massive daily aggregate endpoint shape."""
    calls = []
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.market_data_source.import_module",
        lambda name: SimpleNamespace(
            RESTClient=lambda api_key: _RecordingClient(
                calls,
                [{"t": 1775001600000, "o": 1, "h": 2, "l": 1, "c": 2, "v": 100}],
            )
        ),
    )

    source = MassiveDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))
    source.load()

    assert calls == [
        {
            "ticker": "AAPL",
            "multiplier": 1,
            "timespan": "day",
            "from_": "2026-04-01",
            "to": "2026-04-03",
            "adjusted": False,
            "sort": "asc",
            "limit": 50000,
        }
    ]


def test_load_daily_ohlcv_requires_api_key(monkeypatch) -> None:
    """Massive-backed imports require an explicit local API key."""
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)

    source = MassiveDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))

    with pytest.raises(ValueError, match="MASSIVE_API_KEY is required"):
        source.load()


def test_load_daily_ohlcv_rejects_empty_result(monkeypatch) -> None:
    """The adapter fails clearly when the provider returns no bars."""
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.market_data_source.import_module",
        lambda name: SimpleNamespace(RESTClient=lambda api_key: _Client([])),
    )

    source = MassiveDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))

    with pytest.raises(ValueError, match="No daily OHLCV data returned"):
        source.load()


def test_load_daily_ohlcv_wraps_provider_failure(monkeypatch) -> None:
    """Provider errors are reported without leaking API key material."""
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.market_data_source.import_module",
        lambda name: SimpleNamespace(RESTClient=lambda api_key: _FailingClient()),
    )

    source = MassiveDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))

    with pytest.raises(ValueError, match="Massive.com daily bars fetch failed for AAPL"):
        source.load()


def test_load_daily_ohlcv_rejects_missing_required_field(monkeypatch) -> None:
    """The adapter refuses provider bars missing required OHLCV fields."""
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.market_data_source.import_module",
        lambda name: SimpleNamespace(
            RESTClient=lambda api_key: _Client(
                [{"t": 1775001600000, "o": 1, "h": 2, "l": 1, "v": 100}]
            )
        ),
    )

    source = MassiveDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))

    with pytest.raises(ValueError, match="missing required field"):
        source.load()


def test_load_daily_ohlcv_rejects_invalid_numeric_field(monkeypatch) -> None:
    """The adapter refuses provider bars with invalid numeric values."""
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.market_data_source.import_module",
        lambda name: SimpleNamespace(
            RESTClient=lambda api_key: _Client(
                [{"t": 1775001600000, "o": "bad", "h": 2, "l": 1, "c": 2, "v": 100}]
            )
        ),
    )

    source = MassiveDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))

    with pytest.raises(ValueError, match="invalid open value"):
        source.load()


def test_load_daily_ohlcv_rejects_invalid_date_range() -> None:
    """The adapter guards its own date window boundary."""
    with pytest.raises(ValueError, match="End date must be after start date"):
        MassiveDailyOHLCVImportSource("AAPL", date(2026, 4, 3), date(2026, 4, 3))


class _Client:
    def __init__(self, bars):
        self._bars = bars

    def list_aggs(self, **kwargs):
        return self._bars


class _RecordingClient:
    def __init__(self, calls, bars):
        self._calls = calls
        self._bars = bars

    def list_aggs(self, **kwargs):
        self._calls.append(kwargs)
        return self._bars


class _FailingClient:
    def list_aggs(self, **kwargs):
        raise RuntimeError("rate limit")
