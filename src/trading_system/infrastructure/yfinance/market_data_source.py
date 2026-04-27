"""YFinance-backed daily OHLCV snapshot source adapters."""

from collections.abc import Iterable
from datetime import UTC, date, datetime, time
from importlib import import_module
import math
from typing import Any

from trading_system.ports.market_context import ImportedMarketContext


class YFinanceDailyOHLCVImportSource:
    """Loads one daily OHLCV context snapshot from yfinance."""

    def __init__(self, symbol: str, start: date, end: date) -> None:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Market data symbol is required.")
        if end <= start:
            raise ValueError("End date must be after start date.")

        self._symbol = symbol
        self._start = start
        self._end = end
        self.source_ref = (
            f"symbol={self._symbol};start={self._start.isoformat()};"
            f"end={self._end.isoformat()};interval=1d;auto_adjust=false"
        )

    def load(self) -> ImportedMarketContext:
        """Download daily OHLCV data and convert it into a snapshot payload."""
        provider = self._import_provider()
        download = getattr(provider, "download", None)
        if not callable(download):
            raise ValueError("yfinance download function is unavailable.")

        try:
            frame = download(
                self._symbol,
                start=self._start.isoformat(),
                end=self._end.isoformat(),
                interval="1d",
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=False,
                multi_level_index=False,
            )
        except Exception as exc:  # pragma: no cover - exercised through adapter tests
            raise ValueError(f"yfinance download failed for {self._symbol}: {exc}") from exc

        rows = _daily_bars_from_frame(frame)
        if not rows:
            raise ValueError(f"No daily OHLCV data returned for symbol {self._symbol}.")

        observed_at = datetime.combine(date.fromisoformat(rows[-1]["date"]), time.min, tzinfo=UTC)
        payload = {
            "symbol": self._symbol,
            "provider": "yfinance",
            "interval": "1d",
            "start": self._start.isoformat(),
            "end_exclusive": self._end.isoformat(),
            "auto_adjust": False,
            "bars": rows,
        }
        return ImportedMarketContext(
            context_type="daily_ohlcv",
            observed_at=observed_at,
            payload=payload,
        )

    @staticmethod
    def _import_provider() -> Any:
        try:
            return import_module("yfinance")
        except ModuleNotFoundError as exc:
            raise ValueError("yfinance is not installed.") from exc


def _daily_bars_from_frame(frame: Any) -> list[dict[str, Any]]:
    if frame is None or getattr(frame, "empty", False):
        return []

    columns = getattr(frame, "columns", None)
    if columns is None:
        raise ValueError("yfinance download result is missing OHLCV columns.")

    if any(isinstance(column, tuple) for column in columns):
        raise ValueError("yfinance download result must not use multi-level columns.")

    normalized_columns = [str(column) for column in columns]
    required_columns = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    missing_columns = [column for column in required_columns if column not in normalized_columns]
    if missing_columns:
        raise ValueError(
            "yfinance download result is missing required columns: "
            + ", ".join(missing_columns)
        )

    rows: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        bar_date = _date_from_index(index)
        rows.append(
            {
                "date": bar_date.isoformat(),
                "open": _number(row["Open"], "Open"),
                "high": _number(row["High"], "High"),
                "low": _number(row["Low"], "Low"),
                "close": _number(row["Close"], "Close"),
                "adj_close": _number(row["Adj Close"], "Adj Close"),
                "volume": _integer(row["Volume"], "Volume"),
            }
        )
    return rows


def _date_from_index(index: Any) -> date:
    if isinstance(index, datetime):
        if index.tzinfo is not None:
            return index.astimezone(UTC).date()
        return index.date()
    if isinstance(index, date):
        return index
    if hasattr(index, "to_pydatetime"):
        value = index.to_pydatetime()
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                return value.astimezone(UTC).date()
            return value.date()

    text = str(index)
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise ValueError("yfinance download result contains an invalid bar date.") from exc


def _number(value: Any, column: str) -> float:
    if value is None:
        raise ValueError(f"yfinance download result contains a missing {column} value.")
    numeric = float(value)
    if math.isnan(numeric):
        raise ValueError(f"yfinance download result contains a missing {column} value.")
    return numeric


def _integer(value: Any, column: str) -> int:
    numeric = _number(value, column)
    if not numeric.is_integer():
        raise ValueError(f"yfinance download result contains a non-integer {column} value.")
    return int(numeric)