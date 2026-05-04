"""Alpaca-backed options chain snapshot source adapter."""

from datetime import UTC, date, datetime
import math
import re
from typing import Any

from trading_system.infrastructure.local_secret_vault import require_secret
from trading_system.ports.market_context import ImportedMarketContext


_OCC_SYMBOL_PATTERN = re.compile(
    r"^(?:O:)?(?P<root>[A-Z]{1,6})(?P<expiry>\d{6})(?P<type>[CP])(?P<strike>\d{8})$"
)


class AlpacaOptionsChainImportSource:
    """Loads one options chain context snapshot from Alpaca for a single expiration."""

    def __init__(
        self,
        symbol: str,
        expiration: date,
        *,
        option_client: Any | None = None,
        api_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("Options chain symbol is required.")

        self._symbol = symbol
        self._expiration = expiration
        self._client = option_client
        self._api_key = api_key
        self._secret_key = secret_key
        self.source_ref = (
            f"symbol={self._symbol};expiry={self._expiration.isoformat()};"
            "provider=alpaca;feed=indicative"
        )

    def load(self) -> ImportedMarketContext:
        """Fetch an options chain and convert it into a snapshot payload."""
        expiry_str = self._expiration.isoformat()
        try:
            request = self._option_chain_request()
            result = self._option_client().get_option_chain(request)
            contracts = _contracts_from_result(result, expiry_str)
        except ValueError:
            raise
        except Exception as exc:  # pragma: no cover - exercised through adapter tests
            raise ValueError(
                f"Alpaca options chain fetch failed for {self._symbol} expiry {expiry_str}."
            ) from exc

        if not contracts:
            raise ValueError(
                f"No options contracts returned for {self._symbol} expiry {expiry_str}."
            )

        payload = {
            "symbol": self._symbol,
            "provider": "alpaca",
            "expiration": expiry_str,
            "feed": "indicative",
            "contracts": contracts,
        }
        return ImportedMarketContext(
            context_type="options_chain",
            observed_at=datetime.now(UTC),
            payload=payload,
        )

    def _option_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from alpaca.data.historical import OptionHistoricalDataClient
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise ValueError("alpaca-py is required for Alpaca market data.") from exc
        api_key = self._api_key or require_secret("ALPACA_API_KEY")
        secret_key = self._secret_key or require_secret("ALPACA_SECRET_KEY")
        self._client = OptionHistoricalDataClient(api_key, secret_key)
        return self._client

    def _option_chain_request(self) -> Any:
        try:
            from alpaca.data.enums import OptionsFeed
            from alpaca.data.requests import OptionChainRequest
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise ValueError("alpaca-py is required for Alpaca market data.") from exc
        return OptionChainRequest(
            underlying_symbol=self._symbol,
            expiration_date=self._expiration,
            feed=OptionsFeed.INDICATIVE,
        )


def _contracts_from_result(result: Any, expiry_str: str) -> list[dict[str, Any]]:
    data = result.get("data") if isinstance(result, dict) else getattr(result, "data", None)
    if data is None and isinstance(result, dict):
        data = result
    if data is None:
        return []

    rows: list[dict[str, Any]] = []
    items = data.items() if isinstance(data, dict) else []
    for contract_symbol, snapshot in items:
        parsed = _parse_occ_symbol(str(contract_symbol))
        if parsed is None or parsed["expiration"] != expiry_str:
            continue

        row: dict[str, Any] = {
            "contract_symbol": str(contract_symbol),
            "contract_type": parsed["contract_type"],
            "strike": parsed["strike"],
            "expiration": parsed["expiration"],
        }

        latest_quote = _optional_field(snapshot, "latest_quote", "latestQuote")
        if latest_quote is not None:
            bid = _optional_number(latest_quote, "bid_price", "bp")
            ask = _optional_number(latest_quote, "ask_price", "ap")
            if bid is not None:
                row["bid"] = bid
            if ask is not None:
                row["ask"] = ask

        latest_trade = _optional_field(snapshot, "latest_trade", "latestTrade")
        if latest_trade is not None:
            last_price = _optional_number(latest_trade, "price", "p")
            if last_price is not None:
                row["last_price"] = last_price

        daily_bar = _optional_field(snapshot, "daily_bar", "dailyBar", "day")
        if daily_bar is not None:
            volume = _optional_integer(daily_bar, "volume", "v")
            vwap = _optional_number(daily_bar, "vwap", "vw")
            if volume is not None:
                row["volume"] = volume
            if vwap is not None:
                row["vwap"] = vwap

        open_interest = _optional_integer(snapshot, "open_interest", "openInterest")
        if open_interest is not None:
            row["open_interest"] = open_interest

        implied_volatility = _optional_number(
            snapshot,
            "implied_volatility",
            "impliedVolatility",
        )
        if implied_volatility is not None:
            row["implied_volatility"] = implied_volatility

        greeks = _optional_field(snapshot, "greeks")
        if greeks is not None:
            for greek in ("delta", "gamma", "theta", "vega"):
                value = _optional_number(greeks, greek)
                if value is not None:
                    row[greek] = value

        rows.append(row)
    return rows


def _parse_occ_symbol(contract_symbol: str) -> dict[str, Any] | None:
    match = _OCC_SYMBOL_PATTERN.match(contract_symbol.upper())
    if match is None:
        return None
    expiry_raw = match.group("expiry")
    expiration = f"20{expiry_raw[0:2]}-{expiry_raw[2:4]}-{expiry_raw[4:6]}"
    contract_type = "call" if match.group("type") == "C" else "put"
    strike = int(match.group("strike")) / 1000
    return {
        "expiration": expiration,
        "contract_type": contract_type,
        "strike": float(strike),
    }


def _optional_field(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _optional_number(obj: Any, *names: str) -> float | None:
    value = _optional_field(obj, *names)
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(numeric) else numeric


def _optional_integer(obj: Any, *names: str) -> int | None:
    numeric = _optional_number(obj, *names)
    return None if numeric is None else int(round(numeric))
