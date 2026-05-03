"""Tests for the yfinance options chain snapshot source adapter."""

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from trading_system.infrastructure.yfinance.options_chain_source import (
    YFinanceOptionsChainImportSource,
)


def _make_row(
    contract_symbol: str,
    strike: float,
    last_price: float | None = 2.50,
    bid: float | None = 2.40,
    ask: float | None = 2.60,
    volume: float | None = 1000.0,
    open_interest: float | None = 5000.0,
    implied_volatility: float | None = 0.25,
    in_the_money: bool | None = True,
) -> dict[str, Any]:
    import math

    return {
        "contractSymbol": contract_symbol,
        "strike": strike,
        "lastPrice": last_price if last_price is not None else math.nan,
        "bid": bid if bid is not None else math.nan,
        "ask": ask if ask is not None else math.nan,
        "volume": volume if volume is not None else math.nan,
        "openInterest": open_interest if open_interest is not None else math.nan,
        "impliedVolatility": implied_volatility if implied_volatility is not None else math.nan,
        "inTheMoney": in_the_money,
    }


class _FakeFrame:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.empty = not rows

    def iterrows(self):
        for row in self._rows:
            yield row.get("contractSymbol", ""), SimpleNamespace(**row)


class _FakeChain:
    def __init__(self, calls: list[dict], puts: list[dict]) -> None:
        self.calls = _FakeFrame(calls)
        self.puts = _FakeFrame(puts)


def _make_provider(calls: list[dict], puts: list[dict]):
    chain = _FakeChain(calls, puts)
    return SimpleNamespace(Ticker=lambda symbol: SimpleNamespace(option_chain=lambda expiry: chain))


def test_load_returns_options_chain_context_type(monkeypatch) -> None:
    provider = _make_provider(
        calls=[_make_row("AAPL260516C00185000", 185.0)],
        puts=[_make_row("AAPL260516P00185000", 185.0)],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.options_chain_source.import_module",
        lambda name: provider,
    )
    source = YFinanceOptionsChainImportSource("AAPL", date(2026, 5, 16))
    result = source.load()

    assert result.context_type == "options_chain"
    assert result.payload["symbol"] == "AAPL"
    assert result.payload["provider"] == "yfinance"
    assert result.payload["expiration"] == "2026-05-16"


def test_load_produces_calls_and_puts(monkeypatch) -> None:
    provider = _make_provider(
        calls=[_make_row("AAPL260516C00185000", 185.0)],
        puts=[_make_row("AAPL260516P00185000", 185.0)],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.options_chain_source.import_module",
        lambda name: provider,
    )
    source = YFinanceOptionsChainImportSource("AAPL", date(2026, 5, 16))
    contracts = source.load().payload["contracts"]

    assert len(contracts) == 2
    types = {c["contract_type"] for c in contracts}
    assert types == {"call", "put"}


def test_load_contract_fields(monkeypatch) -> None:
    provider = _make_provider(
        calls=[_make_row("AAPL260516C00185000", 185.0, last_price=3.10, bid=3.00, ask=3.20,
                         volume=500.0, open_interest=2000.0, implied_volatility=0.30,
                         in_the_money=True)],
        puts=[],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.options_chain_source.import_module",
        lambda name: provider,
    )
    source = YFinanceOptionsChainImportSource("AAPL", date(2026, 5, 16))
    contract = source.load().payload["contracts"][0]

    assert contract["contract_symbol"] == "AAPL260516C00185000"
    assert contract["contract_type"] == "call"
    assert contract["strike"] == 185.0
    assert contract["last_price"] == pytest.approx(3.10)
    assert contract["bid"] == pytest.approx(3.00)
    assert contract["ask"] == pytest.approx(3.20)
    assert contract["volume"] == 500
    assert contract["open_interest"] == 2000
    assert contract["implied_volatility"] == pytest.approx(0.30)
    assert contract["in_the_money"] is True


def test_load_volume_rounded_to_integer(monkeypatch) -> None:
    """Volume from yfinance may arrive as a float — must be stored as int."""
    provider = _make_provider(
        calls=[_make_row("AAPL260516C00185000", 185.0, volume=1234.0, open_interest=5678.0)],
        puts=[],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.options_chain_source.import_module",
        lambda name: provider,
    )
    source = YFinanceOptionsChainImportSource("aapl", date(2026, 5, 16))
    contract = source.load().payload["contracts"][0]

    assert isinstance(contract["volume"], int)
    assert isinstance(contract["open_interest"], int)
    assert contract["volume"] == 1234
    assert contract["open_interest"] == 5678


def test_load_symbol_normalised_to_uppercase(monkeypatch) -> None:
    provider = _make_provider(
        calls=[_make_row("AAPL260516C00185000", 185.0)],
        puts=[],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.options_chain_source.import_module",
        lambda name: provider,
    )
    source = YFinanceOptionsChainImportSource("aapl", date(2026, 5, 16))
    assert source.load().payload["symbol"] == "AAPL"


def test_load_empty_chain_raises(monkeypatch) -> None:
    provider = _make_provider(calls=[], puts=[])
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.options_chain_source.import_module",
        lambda name: provider,
    )
    source = YFinanceOptionsChainImportSource("AAPL", date(2026, 5, 16))

    with pytest.raises(ValueError, match="No options contracts returned"):
        source.load()


def test_empty_symbol_raises() -> None:
    with pytest.raises(ValueError, match="symbol is required"):
        YFinanceOptionsChainImportSource("  ", date(2026, 5, 16))


def test_yfinance_unavailable_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.options_chain_source.import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError("yfinance")),
    )
    source = YFinanceOptionsChainImportSource("AAPL", date(2026, 5, 16))

    with pytest.raises(ValueError, match="yfinance is not installed"):
        source.load()
