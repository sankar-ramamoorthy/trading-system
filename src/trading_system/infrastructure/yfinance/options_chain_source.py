"""YFinance-backed options chain snapshot source adapter."""

from datetime import UTC, date, datetime
from importlib import import_module
import math
from typing import Any

from trading_system.ports.market_context import ImportedMarketContext


class YFinanceOptionsChainImportSource:
    """Loads one options chain context snapshot from yfinance for a single expiration."""

    def __init__(self, symbol: str, expiration: date) -> None:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Options chain symbol is required.")

        self._symbol = symbol
        self._expiration = expiration
        self.source_ref = (
            f"symbol={self._symbol};expiry={self._expiration.isoformat()};provider=yfinance"
        )

    def load(self) -> ImportedMarketContext:
        """Fetch an options chain and convert it into a snapshot payload."""
        provider = self._import_provider()
        ticker_cls = getattr(provider, "Ticker", None)
        if not callable(ticker_cls):
            raise ValueError("yfinance Ticker class is unavailable.")

        expiry_str = self._expiration.isoformat()
        try:
            chain = ticker_cls(self._symbol).option_chain(expiry_str)
        except Exception as exc:
            raise ValueError(
                f"yfinance options chain fetch failed for {self._symbol} expiry {expiry_str}."
            ) from exc

        calls = _contracts_from_frame(chain.calls, "call")
        puts = _contracts_from_frame(chain.puts, "put")
        contracts = calls + puts

        if not contracts:
            raise ValueError(
                f"No options contracts returned for {self._symbol} expiry {expiry_str}."
            )

        payload = {
            "symbol": self._symbol,
            "provider": "yfinance",
            "expiration": expiry_str,
            "contracts": contracts,
        }
        return ImportedMarketContext(
            context_type="options_chain",
            observed_at=datetime.now(UTC),
            payload=payload,
        )

    @staticmethod
    def _import_provider() -> Any:
        try:
            return import_module("yfinance")
        except ModuleNotFoundError as exc:
            raise ValueError("yfinance is not installed.") from exc


def _contracts_from_frame(frame: Any, contract_type: str) -> list[dict[str, Any]]:
    if frame is None or getattr(frame, "empty", False):
        return []

    rows: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        contract_symbol = _contract_symbol(index, row)
        strike = _required_number(row, "strike", "strike")
        row_dict: dict[str, Any] = {
            "contract_symbol": contract_symbol,
            "contract_type": contract_type,
            "strike": strike,
            "expiration": _optional_str(row, "contractExpiration") or _optional_str(row, "lastTradeDate") or None,
        }
        last_price = _optional_number(row, "lastPrice")
        if last_price is not None:
            row_dict["last_price"] = last_price
        bid = _optional_number(row, "bid")
        if bid is not None:
            row_dict["bid"] = bid
        ask = _optional_number(row, "ask")
        if ask is not None:
            row_dict["ask"] = ask
        volume = _optional_integer(row, "volume")
        if volume is not None:
            row_dict["volume"] = volume
        open_interest = _optional_integer(row, "openInterest")
        if open_interest is not None:
            row_dict["open_interest"] = open_interest
        iv = _optional_number(row, "impliedVolatility")
        if iv is not None:
            row_dict["implied_volatility"] = iv
        in_the_money = _optional_bool(row, "inTheMoney")
        if in_the_money is not None:
            row_dict["in_the_money"] = in_the_money
        rows.append(row_dict)
    return rows


def _contract_symbol(index: Any, row: Any) -> str:
    sym = _optional_str(row, "contractSymbol")
    if sym:
        return sym
    return str(index)


def _optional_str(row: Any, field: str) -> str | None:
    val = _get(row, field)
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _optional_bool(row: Any, field: str) -> bool | None:
    val = _get(row, field)
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, float) and math.isnan(val):
        return None
    return bool(val)


def _required_number(row: Any, field: str, label: str) -> float:
    val = _get(row, field)
    if val is None:
        raise ValueError(f"yfinance options contract is missing required field: {label}")
    try:
        num = float(val)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"yfinance options contract has invalid {label} value.") from exc
    if math.isnan(num):
        raise ValueError(f"yfinance options contract is missing required field: {label}")
    return num


def _optional_number(row: Any, field: str) -> float | None:
    val = _get(row, field)
    if val is None:
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(num) else num


def _optional_integer(row: Any, field: str) -> int | None:
    num = _optional_number(row, field)
    return None if num is None else int(round(num))


def _get(row: Any, field: str) -> Any:
    if isinstance(row, dict):
        return row.get(field)
    try:
        return row[field]
    except (KeyError, TypeError):
        pass
    return getattr(row, field, None)
