"""Tests for the Alpaca options chain snapshot source adapter."""

from datetime import date
from types import SimpleNamespace

import pytest

from trading_system.infrastructure.alpaca.options_chain_source import (
    AlpacaOptionsChainImportSource,
)
from trading_system.infrastructure.local_secret_vault import LocalSecretVaultError


def test_load_returns_options_chain_context_type() -> None:
    """The adapter converts Alpaca option snapshots into context payloads."""
    client = _OptionClient(
        {
            "AAPL260516C00185000": _snapshot(
                bid=2.40,
                ask=2.60,
                last_price=2.50,
                volume=1000,
                open_interest=5000,
                implied_volatility=0.25,
            )
        }
    )

    source = AlpacaOptionsChainImportSource(
        "aapl",
        date(2026, 5, 16),
        option_client=client,
    )
    result = source.load()

    assert result.context_type == "options_chain"
    assert result.payload["symbol"] == "AAPL"
    assert result.payload["provider"] == "alpaca"
    assert result.payload["expiration"] == "2026-05-16"
    assert result.payload["feed"] == "indicative"


def test_load_uses_expected_client_call() -> None:
    """The adapter requests a single-expiration indicative options chain."""
    client = _OptionClient({"AAPL260516C00185000": _snapshot()})

    source = AlpacaOptionsChainImportSource(
        "AAPL",
        date(2026, 5, 16),
        option_client=client,
    )
    source.load()

    request = client.requests[0]
    assert request.underlying_symbol == "AAPL"
    assert request.expiration_date == date(2026, 5, 16)
    assert request.feed.value == "indicative"


def test_load_contract_fields() -> None:
    """Snapshot quote, trade, and risk fields map to the stable contract shape."""
    client = _OptionClient(
        {
            "AAPL260516C00185000": _snapshot(
                bid=3.00,
                ask=3.20,
                last_price=3.10,
                volume=500,
                open_interest=2000,
                implied_volatility=0.30,
                delta=0.52,
                gamma=0.03,
                theta=-0.08,
                vega=0.15,
            ),
            "AAPL260516P00180000": _snapshot(bid=1.00, ask=1.20),
        }
    )
    source = AlpacaOptionsChainImportSource(
        "AAPL",
        date(2026, 5, 16),
        option_client=client,
    )

    contracts = source.load().payload["contracts"]

    assert contracts[0] == {
        "contract_symbol": "AAPL260516C00185000",
        "contract_type": "call",
        "strike": 185.0,
        "expiration": "2026-05-16",
        "bid": 3.00,
        "ask": 3.20,
        "last_price": 3.10,
        "volume": 500,
        "open_interest": 2000,
        "implied_volatility": 0.30,
        "delta": 0.52,
        "gamma": 0.03,
        "theta": -0.08,
        "vega": 0.15,
    }
    assert contracts[1]["contract_type"] == "put"
    assert contracts[1]["strike"] == 180.0


def test_load_filters_to_requested_expiration() -> None:
    """Contracts outside the requested expiry are ignored."""
    client = _OptionClient(
        {
            "AAPL260516C00185000": _snapshot(),
            "AAPL260620C00190000": _snapshot(),
        }
    )
    source = AlpacaOptionsChainImportSource(
        "AAPL",
        date(2026, 5, 16),
        option_client=client,
    )

    contracts = source.load().payload["contracts"]

    assert len(contracts) == 1
    assert contracts[0]["contract_symbol"] == "AAPL260516C00185000"


def test_load_missing_api_key_raises(monkeypatch, tmp_path) -> None:
    """Alpaca options imports require reserved Alpaca credentials."""
    import trading_system.infrastructure.local_secret_vault as secret_vault

    monkeypatch.setattr(secret_vault, "DEFAULT_VAULT_PATH", tmp_path / "keys.enc")
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    source = AlpacaOptionsChainImportSource("AAPL", date(2026, 5, 16))

    with pytest.raises(LocalSecretVaultError, match="ALPACA_API_KEY is required"):
        source.load()


def test_load_no_contracts_for_expiry_raises() -> None:
    """The adapter fails clearly when no matching contracts are returned."""
    source = AlpacaOptionsChainImportSource(
        "AAPL",
        date(2026, 5, 16),
        option_client=_OptionClient({"AAPL260620C00190000": _snapshot()}),
    )

    with pytest.raises(ValueError, match="No options contracts returned"):
        source.load()


def test_empty_symbol_raises() -> None:
    """The adapter requires a non-empty underlying symbol."""
    with pytest.raises(ValueError, match="symbol is required"):
        AlpacaOptionsChainImportSource("  ", date(2026, 5, 16))


def _snapshot(
    *,
    bid: float | None = 2.40,
    ask: float | None = 2.60,
    last_price: float | None = 2.50,
    volume: int | None = 1000,
    open_interest: int | None = 5000,
    implied_volatility: float | None = 0.25,
    delta: float | None = None,
    gamma: float | None = None,
    theta: float | None = None,
    vega: float | None = None,
):
    return SimpleNamespace(
        latest_quote=SimpleNamespace(bid_price=bid, ask_price=ask),
        latest_trade=SimpleNamespace(price=last_price),
        daily_bar=SimpleNamespace(volume=volume),
        open_interest=open_interest,
        implied_volatility=implied_volatility,
        greeks=SimpleNamespace(delta=delta, gamma=gamma, theta=theta, vega=vega),
    )


class _OptionClient:
    def __init__(self, data):
        self._data = data
        self.requests = []

    def get_option_chain(self, request):
        self.requests.append(request)
        return self._data
