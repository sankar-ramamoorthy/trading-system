"""Massive.com-backed daily OHLCV snapshot source adapters."""

from collections.abc import Iterable
from datetime import UTC, date, datetime, time
from importlib import import_module
import math
import os
from typing import Any

from trading_system.ports.market_context import ImportedMarketContext


class MassiveDailyOHLCVImportSource:
    """Loads one daily OHLCV context snapshot from Massive.com."""

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
            f"end={self._end.isoformat()};provider=massive;timespan=day;"
            "adjusted=false"
        )

    def load(self) -> ImportedMarketContext:
        """Fetch daily aggregate bars and convert them into a snapshot payload."""
        api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("MASSIVE_API_KEY is required for Massive.com market data.")

        provider = self._import_provider()
        rest_client = getattr(provider, "RESTClient", None)
        if not callable(rest_client):
            raise ValueError("Massive.com RESTClient is unavailable.")

        try:
            client = rest_client(api_key=api_key)
            provider_bars = client.list_aggs(
                ticker=self._symbol,
                multiplier=1,
                timespan="day",
                from_=self._start.isoformat(),
                to=self._end.isoformat(),
                adjusted=False,
                sort="asc",
                limit=50000,
            )
            rows = _daily_bars_from_aggs(provider_bars)
        except ValueError:
            raise
        except Exception as exc:  # pragma: no cover - exercised through adapter tests
            raise ValueError(
                f"Massive.com daily bars fetch failed for {self._symbol}."
            ) from exc

        if not rows:
            raise ValueError(f"No daily OHLCV data returned for symbol {self._symbol}.")

        observed_at = datetime.combine(date.fromisoformat(rows[-1]["date"]), time.min, tzinfo=UTC)
        payload = {
            "symbol": self._symbol,
            "provider": "massive",
            "interval": "1d",
            "timespan": "day",
            "start": self._start.isoformat(),
            "end": self._end.isoformat(),
            "adjusted": False,
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
            return import_module("massive")
        except ModuleNotFoundError as exc:
            raise ValueError("massive is not installed.") from exc


def _daily_bars_from_aggs(aggs: Iterable[Any] | None) -> list[dict[str, Any]]:
    if aggs is None:
        return []

    rows: list[dict[str, Any]] = []
    for agg in aggs:
        bar_date = _date_from_timestamp(_required_field(agg, "timestamp", "t"))
        row = {
            "date": bar_date.isoformat(),
            "open": _number(_required_field(agg, "open", "o"), "open"),
            "high": _number(_required_field(agg, "high", "h"), "high"),
            "low": _number(_required_field(agg, "low", "l"), "low"),
            "close": _number(_required_field(agg, "close", "c"), "close"),
            "volume": _integer(_required_field(agg, "volume", "v"), "volume"),
        }

        vwap = _optional_field(agg, "vwap", "vw")
        if vwap is not None:
            row["vwap"] = _number(vwap, "vwap")

        transactions = _optional_field(agg, "transactions", "n")
        if transactions is not None:
            row["transactions"] = _integer(transactions, "transactions")

        otc = _optional_field(agg, "otc")
        if otc is not None:
            row["otc"] = bool(otc)

        rows.append(row)
    return rows


def _required_field(agg: Any, *names: str) -> Any:
    value = _optional_field(agg, *names)
    if value is None:
        raise ValueError(
            "Massive.com daily bar is missing required field: " + "/".join(names)
        )
    return value


def _optional_field(agg: Any, *names: str) -> Any:
    for name in names:
        if isinstance(agg, dict) and name in agg:
            return agg[name]
        if hasattr(agg, name):
            return getattr(agg, name)
    return None


def _date_from_timestamp(value: Any) -> date:
    timestamp_ms = _integer(value, "timestamp")
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).date()
    except (OSError, OverflowError, ValueError) as exc:
        raise ValueError("Massive.com daily bar contains an invalid timestamp.") from exc


def _number(value: Any, field: str) -> float:
    if value is None:
        raise ValueError(f"Massive.com daily bar contains a missing {field} value.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Massive.com daily bar contains an invalid {field} value."
        ) from exc
    if math.isnan(numeric):
        raise ValueError(f"Massive.com daily bar contains a missing {field} value.")
    return numeric


def _integer(value: Any, field: str) -> int:
    numeric = _number(value, field)
    if not numeric.is_integer():
        raise ValueError(f"Massive.com daily bar contains a non-integer {field} value.")
    return int(numeric)
