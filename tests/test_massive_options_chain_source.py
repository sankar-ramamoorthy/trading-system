"""Tests for the Massive.com options chain snapshot source adapter."""

from datetime import date
from types import SimpleNamespace

import pytest

from trading_system.infrastructure.massive.options_chain_source import (
    MassiveOptionsChainImportSource,
)


def _make_snapshot(
    ticker: str,
    contract_type: str,
    strike: float,
    expiration: str,
    bid: float | None = 2.40,
    ask: float | None = 2.60,
    last_price: float | None = 2.50,
    volume: float | None = 1000.0,
    open_interest: int | None = 5000,
    implied_volatility: float | None = 0.25,
    delta: float | None = None,
    gamma: float | None = None,
    theta: float | None = None,
    vega: float | None = None,
):
    details = SimpleNamespace(
        ticker=ticker,
        contract_type=contract_type,
        strike_price=strike,
        expiration_date=expiration,
    )
    last_quote = SimpleNamespace(bid=bid, ask=ask)
    last_trade = SimpleNamespace(price=last_price)
    day = SimpleNamespace(volume=volume, vwap=None)
    greeks = SimpleNamespace(delta=delta, gamma=gamma, theta=theta, vega=vega)
    return SimpleNamespace(
        details=details,
        last_quote=last_quote,
        last_trade=last_trade,
        day=day,
        open_interest=open_interest,
        implied_volatility=implied_volatility,
        greeks=greeks,
        ticker=ticker,
    )


def _make_client(snapshots):
    return SimpleNamespace(
        list_snapshot_options_chain=lambda underlying_asset: snapshots
    )


def _make_provider(snapshots):
    client = _make_client(snapshots)
    return SimpleNamespace(RESTClient=lambda api_key: client)


def test_load_returns_options_chain_context_type(monkeypatch) -> None:
    snaps = [
        _make_snapshot("O:AAPL260516C00185000", "call", 185.0, "2026-05-16"),
    ]
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.options_chain_source.import_module",
        lambda name: _make_provider(snaps),
    )
    source = MassiveOptionsChainImportSource("AAPL", date(2026, 5, 16))
    result = source.load()

    assert result.context_type == "options_chain"
    assert result.payload["symbol"] == "AAPL"
    assert result.payload["provider"] == "massive"
    assert result.payload["expiration"] == "2026-05-16"


def test_load_filters_to_requested_expiration(monkeypatch) -> None:
    snaps = [
        _make_snapshot("O:AAPL260516C00185000", "call", 185.0, "2026-05-16"),
        _make_snapshot("O:AAPL260620C00190000", "call", 190.0, "2026-06-20"),
    ]
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.options_chain_source.import_module",
        lambda name: _make_provider(snaps),
    )
    source = MassiveOptionsChainImportSource("AAPL", date(2026, 5, 16))
    contracts = source.load().payload["contracts"]

    assert len(contracts) == 1
    assert contracts[0]["contract_symbol"] == "O:AAPL260516C00185000"
    assert contracts[0]["expiration"] == "2026-05-16"


def test_load_contract_fields(monkeypatch) -> None:
    snaps = [
        _make_snapshot(
            "O:AAPL260516C00185000", "call", 185.0, "2026-05-16",
            bid=3.00, ask=3.20, last_price=3.10,
            volume=500.0, open_interest=2000,
            implied_volatility=0.30,
        ),
    ]
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.options_chain_source.import_module",
        lambda name: _make_provider(snaps),
    )
    source = MassiveOptionsChainImportSource("AAPL", date(2026, 5, 16))
    contract = source.load().payload["contracts"][0]

    assert contract["contract_symbol"] == "O:AAPL260516C00185000"
    assert contract["contract_type"] == "call"
    assert contract["strike"] == pytest.approx(185.0)
    assert contract["bid"] == pytest.approx(3.00)
    assert contract["ask"] == pytest.approx(3.20)
    assert contract["last_price"] == pytest.approx(3.10)
    assert contract["volume"] == 500
    assert contract["open_interest"] == 2000
    assert contract["implied_volatility"] == pytest.approx(0.30)


def test_load_includes_greeks_when_available(monkeypatch) -> None:
    snaps = [
        _make_snapshot(
            "O:AAPL260516C00185000", "call", 185.0, "2026-05-16",
            delta=0.52, gamma=0.03, theta=-0.08, vega=0.15,
        ),
    ]
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.options_chain_source.import_module",
        lambda name: _make_provider(snaps),
    )
    source = MassiveOptionsChainImportSource("AAPL", date(2026, 5, 16))
    contract = source.load().payload["contracts"][0]

    assert contract["delta"] == pytest.approx(0.52)
    assert contract["gamma"] == pytest.approx(0.03)
    assert contract["theta"] == pytest.approx(-0.08)
    assert contract["vega"] == pytest.approx(0.15)


def test_load_omits_greeks_when_none(monkeypatch) -> None:
    snaps = [
        _make_snapshot("O:AAPL260516C00185000", "call", 185.0, "2026-05-16"),
    ]
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.options_chain_source.import_module",
        lambda name: _make_provider(snaps),
    )
    source = MassiveOptionsChainImportSource("AAPL", date(2026, 5, 16))
    contract = source.load().payload["contracts"][0]

    for greek in ("delta", "gamma", "theta", "vega"):
        assert greek not in contract


def test_load_no_contracts_for_expiry_raises(monkeypatch) -> None:
    snaps = [
        _make_snapshot("O:AAPL260620C00190000", "call", 190.0, "2026-06-20"),
    ]
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.options_chain_source.import_module",
        lambda name: _make_provider(snaps),
    )
    source = MassiveOptionsChainImportSource("AAPL", date(2026, 5, 16))

    with pytest.raises(ValueError, match="No options contracts returned"):
        source.load()


def test_load_missing_api_key_raises(monkeypatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.options_chain_source.import_module",
        lambda name: _make_provider([]),
    )
    source = MassiveOptionsChainImportSource("AAPL", date(2026, 5, 16))

    with pytest.raises(ValueError, match="MASSIVE_API_KEY is required"):
        source.load()


def test_empty_symbol_raises() -> None:
    with pytest.raises(ValueError, match="symbol is required"):
        MassiveOptionsChainImportSource("  ", date(2026, 5, 16))


def test_massive_unavailable_raises(monkeypatch) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", "test-key")
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.options_chain_source.import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError("massive")),
    )
    source = MassiveOptionsChainImportSource("AAPL", date(2026, 5, 16))

    with pytest.raises(ValueError, match="massive is not installed"):
        source.load()
