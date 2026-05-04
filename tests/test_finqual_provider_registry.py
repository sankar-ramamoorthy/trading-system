"""Tests for Finqual provider selection."""

import pytest

from trading_system.infrastructure.finqual_providers import FinqualProviderRegistry


def test_registry_resolves_financial_statement_source() -> None:
    """The registry returns Finqual source metadata for statements."""
    selection = FinqualProviderRegistry().create_financial_statement_source(
        provider="FINQUAL",
        symbol="aapl",
        statement="income-statement",
        start=2024,
        end=2025,
        quarter=False,
    )

    assert selection.source == "finqual"
    assert selection.source_ref == (
        "symbol=AAPL;statement=income-statement;start=2024;end=2025;"
        "quarter=false;provider=finqual"
    )
    assert callable(selection.source_adapter.load)


def test_registry_resolves_insider_transactions_source() -> None:
    """The registry returns Finqual source metadata for insider transactions."""
    selection = FinqualProviderRegistry().create_insider_transactions_source(
        provider="FINQUAL",
        symbol="nvda",
        period="1m",
    )

    assert selection.source == "finqual"
    assert selection.source_ref == (
        "symbol=NVDA;period=1m;provider=finqual;dataset=insider-transactions"
    )
    assert callable(selection.source_adapter.load)


def test_registry_resolves_13f_source() -> None:
    """The registry returns Finqual source metadata for 13F holdings."""
    selection = FinqualProviderRegistry().create_13f_source(
        provider="FINQUAL",
        cik="0001067983",
        period=1,
    )

    assert selection.source == "finqual"
    assert selection.source_ref == "cik=0001067983;period=1;provider=finqual;dataset=13f"
    assert callable(selection.source_adapter.load)


def test_registry_rejects_unsupported_provider() -> None:
    """Only Finqual can be selected through the Finqual provider registry."""
    with pytest.raises(ValueError, match="Finqual provider is not supported"):
        FinqualProviderRegistry().create_insider_transactions_source(
            provider="massive",
            symbol="AAPL",
            period="1m",
        )
