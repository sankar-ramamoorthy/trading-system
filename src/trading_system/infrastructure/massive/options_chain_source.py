"""Massive.com-backed options chain snapshot source adapter."""

from datetime import UTC, date, datetime
from importlib import import_module
import math
import os
from typing import Any

from trading_system.ports.market_context import ImportedMarketContext


class MassiveOptionsChainImportSource:
    """Loads one options chain context snapshot from Massive.com for a single expiration."""

    def __init__(self, symbol: str, expiration: date) -> None:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Options chain symbol is required.")

        self._symbol = symbol
        self._expiration = expiration
        self.source_ref = (
            f"symbol={self._symbol};expiry={self._expiration.isoformat()};provider=massive"
        )

    def load(self) -> ImportedMarketContext:
        """Fetch options chain from Massive.com and convert it into a snapshot payload."""
        api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("MASSIVE_API_KEY is required for Massive.com options data.")

        provider = self._import_provider()
        rest_client = getattr(provider, "RESTClient", None)
        if not callable(rest_client):
            raise ValueError("Massive.com RESTClient is unavailable.")

        expiry_str = self._expiration.isoformat()
        try:
            client = rest_client(api_key=api_key)
            snapshots = client.list_snapshot_options_chain(self._symbol)
            contracts = _contracts_from_snapshots(snapshots, expiry_str)
        except ValueError:
            raise
        except Exception as exc:
            detail = str(exc)
            if "NOT_AUTHORIZED" in detail or "not entitled" in detail.lower():
                raise ValueError(
                    "Massive.com options chain requires a paid plan. "
                    "Upgrade at https://massive.com/pricing or use --provider yfinance."
                ) from exc
            raise ValueError(
                f"Massive.com options chain fetch failed for {self._symbol}."
            ) from exc

        if not contracts:
            raise ValueError(
                f"No options contracts returned for {self._symbol} expiry {expiry_str}."
            )

        payload = {
            "symbol": self._symbol,
            "provider": "massive",
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
            return import_module("massive")
        except ModuleNotFoundError as exc:
            raise ValueError("massive is not installed.") from exc


def _contracts_from_snapshots(
    snapshots: Any, expiry_str: str
) -> list[dict[str, Any]]:
    if snapshots is None:
        return []

    rows: list[dict[str, Any]] = []
    for snap in snapshots:
        details = _optional_field(snap, "details")
        if details is None:
            continue

        snap_expiry = _optional_str(details, "expiration_date")
        if snap_expiry != expiry_str:
            continue

        contract_type_raw = _optional_str(details, "contract_type") or ""
        contract_type = contract_type_raw.lower()
        if contract_type not in ("call", "put"):
            continue

        strike = _optional_number(details, "strike_price")
        if strike is None:
            continue

        ticker = _optional_str(details, "ticker") or _optional_str(snap, "ticker") or ""

        row: dict[str, Any] = {
            "contract_symbol": ticker,
            "contract_type": contract_type,
            "strike": strike,
            "expiration": expiry_str,
        }

        last_quote = _optional_field(snap, "last_quote")
        if last_quote is not None:
            bid = _optional_number(last_quote, "bid")
            ask = _optional_number(last_quote, "ask")
            if bid is not None:
                row["bid"] = bid
            if ask is not None:
                row["ask"] = ask

        last_trade = _optional_field(snap, "last_trade")
        if last_trade is not None:
            price = _optional_number(last_trade, "price")
            if price is not None:
                row["last_price"] = price

        day = _optional_field(snap, "day")
        if day is not None:
            volume = _optional_integer(day, "volume")
            vwap = _optional_number(day, "vwap")
            if volume is not None:
                row["volume"] = volume
            if vwap is not None:
                row["vwap"] = vwap

        oi = _optional_integer(snap, "open_interest")
        if oi is not None:
            row["open_interest"] = oi

        iv = _optional_number(snap, "implied_volatility")
        if iv is not None:
            row["implied_volatility"] = iv

        greeks = _optional_field(snap, "greeks")
        if greeks is not None:
            for greek in ("delta", "gamma", "theta", "vega"):
                val = _optional_number(greeks, greek)
                if val is not None:
                    row[greek] = val

        rows.append(row)
    return rows


def _optional_field(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _optional_str(obj: Any, field: str) -> str | None:
    val = _optional_field(obj, field)
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _optional_number(obj: Any, field: str) -> float | None:
    val = _optional_field(obj, field)
    if val is None:
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(num) else num


def _optional_integer(obj: Any, field: str) -> int | None:
    num = _optional_number(obj, field)
    return None if num is None else int(round(num))
