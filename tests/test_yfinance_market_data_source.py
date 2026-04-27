"""Tests for the yfinance daily OHLCV snapshot source adapter."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from trading_system.infrastructure.yfinance.market_data_source import (
    YFinanceDailyOHLCVImportSource,
)


def test_load_daily_ohlcv_payload_from_provider_result(monkeypatch) -> None:
    """The adapter converts provider bars into a stable snapshot payload."""
    frame = _Frame(
        columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"],
        rows=[
            (
                datetime(2026, 4, 1, 0, 0),
                {
                    "Open": 100.0,
                    "High": 105.0,
                    "Low": 99.5,
                    "Close": 104.0,
                    "Adj Close": 103.5,
                    "Volume": 1000,
                },
            ),
            (
                datetime(2026, 4, 2, 0, 0),
                {
                    "Open": 104.0,
                    "High": 106.0,
                    "Low": 101.0,
                    "Close": 105.5,
                    "Adj Close": 105.0,
                    "Volume": 1200,
                },
            ),
        ],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.market_data_source.import_module",
        lambda name: SimpleNamespace(download=lambda *args, **kwargs: frame),
    )

    source = YFinanceDailyOHLCVImportSource("aapl", date(2026, 4, 1), date(2026, 4, 3))
    imported = source.load()

    assert imported.context_type == "daily_ohlcv"
    assert imported.observed_at.isoformat() == "2026-04-02T00:00:00+00:00"
    assert imported.payload["symbol"] == "AAPL"
    assert imported.payload["provider"] == "yfinance"
    assert imported.payload["interval"] == "1d"
    assert imported.payload["start"] == "2026-04-01"
    assert imported.payload["end_exclusive"] == "2026-04-03"
    assert imported.payload["auto_adjust"] is False
    assert imported.payload["bars"] == [
        {
            "date": "2026-04-01",
            "open": 100.0,
            "high": 105.0,
            "low": 99.5,
            "close": 104.0,
            "adj_close": 103.5,
            "volume": 1000,
        },
        {
            "date": "2026-04-02",
            "open": 104.0,
            "high": 106.0,
            "low": 101.0,
            "close": 105.5,
            "adj_close": 105.0,
            "volume": 1200,
        },
    ]


def test_load_daily_ohlcv_rejects_empty_result(monkeypatch) -> None:
    """The adapter fails clearly when the provider returns no bars."""
    frame = _Frame(columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"], rows=[])
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.market_data_source.import_module",
        lambda name: SimpleNamespace(download=lambda *args, **kwargs: frame),
    )

    source = YFinanceDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))

    with pytest.raises(ValueError, match="No daily OHLCV data returned"):
        source.load()


def test_load_daily_ohlcv_rejects_missing_columns(monkeypatch) -> None:
    """The adapter refuses provider frames missing required OHLCV fields."""
    frame = _Frame(
        columns=["Open", "High", "Low", "Close"],
        rows=[(date(2026, 4, 1), {"Open": 1, "High": 2, "Low": 1, "Close": 2})],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.market_data_source.import_module",
        lambda name: SimpleNamespace(download=lambda *args, **kwargs: frame),
    )

    source = YFinanceDailyOHLCVImportSource("AAPL", date(2026, 4, 1), date(2026, 4, 3))

    with pytest.raises(ValueError, match="missing required columns"):
        source.load()


def test_load_daily_ohlcv_rejects_invalid_date_range() -> None:
    """The adapter guards its own date window boundary."""
    with pytest.raises(ValueError, match="End date must be after start date"):
        YFinanceDailyOHLCVImportSource("AAPL", date(2026, 4, 3), date(2026, 4, 3))


class _Frame:
    def __init__(self, *, columns: list[str], rows: list[tuple[object, dict[str, object]]]) -> None:
        self.columns = columns
        self._rows = rows

    @property
    def empty(self) -> bool:
        return not self._rows

    def iterrows(self):
        return iter(self._rows)