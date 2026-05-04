"""Alpaca-backed daily OHLCV snapshot source adapter."""

from datetime import UTC, date, datetime, time
import math
from typing import Any

from trading_system.infrastructure.local_secret_vault import require_secret
from trading_system.ports.market_context import ImportedMarketContext


class AlpacaDailyOHLCVImportSource:
    """Loads one daily OHLCV context snapshot from Alpaca market data."""

    def __init__(
        self,
        symbol: str,
        start: date,
        end: date,
        *,
        stock_client: Any | None = None,
        api_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Market data symbol is required.")
        if end <= start:
            raise ValueError("End date must be after start date.")

        self._symbol = symbol
        self._start = start
        self._end = end
        self._client = stock_client
        self._api_key = api_key
        self._secret_key = secret_key
        self.source_ref = (
            f"symbol={self._symbol};start={self._start.isoformat()};"
            f"end={self._end.isoformat()};provider=alpaca;interval=1d;"
            "feed=iex;adjustment=raw"
        )

    def load(self) -> ImportedMarketContext:
        """Fetch daily stock bars and convert them into a snapshot payload."""
        try:
            request = self._stock_bars_request()
            result = self._stock_client().get_stock_bars(request)
            rows = _daily_bars_from_result(result, self._symbol)
        except ValueError:
            raise
        except Exception as exc:  # pragma: no cover - exercised through adapter tests
            raise ValueError(f"Alpaca daily bars fetch failed for {self._symbol}.") from exc

        if not rows:
            raise ValueError(f"No daily OHLCV data returned for symbol {self._symbol}.")

        observed_at = datetime.combine(date.fromisoformat(rows[-1]["date"]), time.min, tzinfo=UTC)
        payload = {
            "symbol": self._symbol,
            "provider": "alpaca",
            "interval": "1d",
            "feed": "iex",
            "adjustment": "raw",
            "start": self._start.isoformat(),
            "end": self._end.isoformat(),
            "bars": rows,
        }
        return ImportedMarketContext(
            context_type="daily_ohlcv",
            observed_at=observed_at,
            payload=payload,
        )

    def _stock_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from alpaca.data.historical import StockHistoricalDataClient
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise ValueError("alpaca-py is required for Alpaca market data.") from exc
        api_key = self._api_key or require_secret("ALPACA_API_KEY")
        secret_key = self._secret_key or require_secret("ALPACA_SECRET_KEY")
        self._client = StockHistoricalDataClient(api_key, secret_key)
        return self._client

    def _stock_bars_request(self) -> Any:
        try:
            from alpaca.data.enums import Adjustment, DataFeed
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise ValueError("alpaca-py is required for Alpaca market data.") from exc
        return StockBarsRequest(
            symbol_or_symbols=self._symbol,
            start=datetime.combine(self._start, time.min, tzinfo=UTC),
            end=datetime.combine(self._end, time.min, tzinfo=UTC),
            timeframe=TimeFrame.Day,
            feed=DataFeed.IEX,
            adjustment=Adjustment.RAW,
        )


def _daily_bars_from_result(result: Any, symbol: str) -> list[dict[str, Any]]:
    data = result.get("data") if isinstance(result, dict) else getattr(result, "data", None)
    if data is None and isinstance(result, dict):
        data = result
    if data is None:
        return []

    bars = None
    if isinstance(data, dict):
        bars = data.get(symbol) or data.get(symbol.upper())
    if bars is None:
        return []

    rows: list[dict[str, Any]] = []
    for bar in bars:
        if bar is None:
            continue
        row = {
            "date": _date_from_timestamp(_required_field(bar, "timestamp", "t")).isoformat(),
            "open": _number(_required_field(bar, "open", "o"), "open"),
            "high": _number(_required_field(bar, "high", "h"), "high"),
            "low": _number(_required_field(bar, "low", "l"), "low"),
            "close": _number(_required_field(bar, "close", "c"), "close"),
            "volume": _integer(_required_field(bar, "volume", "v"), "volume"),
        }

        vwap = _optional_field(bar, "vwap", "vw")
        if vwap is not None:
            row["vwap"] = _number(vwap, "vwap")

        trade_count = _optional_field(bar, "trade_count", "n")
        if trade_count is not None:
            row["trade_count"] = _integer(trade_count, "trade_count")

        rows.append(row)
    return rows


def _required_field(item: Any, *names: str) -> Any:
    value = _optional_field(item, *names)
    if value is None:
        raise ValueError("Alpaca daily bar is missing required field: " + "/".join(names))
    return value


def _optional_field(item: Any, *names: str) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return None


def _date_from_timestamp(value: Any) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).date()
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError("Alpaca daily bar contains an invalid timestamp.") from exc


def _number(value: Any, field: str) -> float:
    if value is None:
        raise ValueError(f"Alpaca daily bar contains a missing {field} value.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Alpaca daily bar contains an invalid {field} value.") from exc
    if math.isnan(numeric):
        raise ValueError(f"Alpaca daily bar contains a missing {field} value.")
    return numeric


def _integer(value: Any, field: str) -> int:
    return int(round(_number(value, field)))
