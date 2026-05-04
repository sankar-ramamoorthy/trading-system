"""Tests for Finqual fundamentals and ownership snapshot adapters."""

from urllib.parse import parse_qs, urlparse

import pytest

from trading_system.infrastructure.finqual.context_sources import (
    Finqual13FImportSource,
    FinqualFinancialStatementImportSource,
    FinqualInsiderTransactionsImportSource,
)
from trading_system.infrastructure.local_secret_vault import LocalSecretVaultError


def test_financial_statement_loads_payload_and_query_shape() -> None:
    """The statement adapter wraps Finqual JSON without leaking the API key."""
    calls = []

    source = FinqualFinancialStatementImportSource(
        "aapl",
        "income-statement",
        2024,
        2025,
        api_key="secret-key",
        http_get=_fake_http_get(calls, {"items": [{"date": "2025-09-30"}]}),
    )
    imported = source.load()

    url = calls[0]
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.path == "/income-statement"
    assert query["ticker"] == ["AAPL"]
    assert query["start"] == ["2024"]
    assert query["end"] == ["2025"]
    assert query["quarter"] == ["false"]
    assert query["api_key"] == ["secret-key"]
    assert imported.context_type == "financial_statement"
    assert imported.payload == {
        "symbol": "AAPL",
        "provider": "finqual",
        "statement": "income-statement",
        "start": 2024,
        "end": 2025,
        "quarter": False,
        "data": {"items": [{"date": "2025-09-30"}]},
    }
    assert "secret-key" not in source.source_ref
    assert "secret-key" not in repr(imported.payload)


def test_financial_statement_supports_quarterly_balance_sheet() -> None:
    """The adapter supports the accepted statement path set and quarter flag."""
    calls = []
    source = FinqualFinancialStatementImportSource(
        "nvda",
        "balance-sheet",
        2024,
        2024,
        quarter=True,
        api_key="secret-key",
        http_get=_fake_http_get(calls, []),
    )

    imported = source.load()

    parsed = urlparse(calls[0])
    assert parsed.path == "/balance-sheet"
    assert parse_qs(parsed.query)["quarter"] == ["true"]
    assert imported.payload["statement"] == "balance-sheet"
    assert imported.payload["data"] == []


def test_financial_statement_rejects_unsupported_statement() -> None:
    """Only explicitly accepted statement endpoints can be selected."""
    with pytest.raises(ValueError, match="statement type is not supported"):
        FinqualFinancialStatementImportSource("AAPL", "ratios", 2024, 2025)


def test_financial_statement_requires_api_key(monkeypatch, tmp_path) -> None:
    """Finqual imports require the reserved Finqual credential."""
    import trading_system.infrastructure.local_secret_vault as secret_vault

    monkeypatch.setattr(secret_vault, "DEFAULT_VAULT_PATH", tmp_path / "keys.enc")
    monkeypatch.delenv("FINQUAL_API_KEY", raising=False)

    source = FinqualFinancialStatementImportSource("AAPL", "cash-flow", 2024, 2025)

    with pytest.raises(LocalSecretVaultError, match="FINQUAL_API_KEY is required"):
        source.load()


def test_financial_statement_wraps_provider_failure_without_secret() -> None:
    """Provider failures do not expose URL query strings or key material."""
    source = FinqualFinancialStatementImportSource(
        "AAPL",
        "income-statement",
        2024,
        2025,
        api_key="secret-key",
        http_get=lambda url: (_ for _ in ()).throw(RuntimeError("secret-key")),
    )

    with pytest.raises(ValueError) as exc_info:
        source.load()

    assert "Finqual financial statement fetch failed for AAPL" in str(exc_info.value)
    assert "secret-key" not in str(exc_info.value)


def test_insider_transactions_loads_payload_and_query_shape() -> None:
    """The insider adapter stores ticker, period, and provider response."""
    calls = []
    source = FinqualInsiderTransactionsImportSource(
        "nvda",
        "1m",
        api_key="secret-key",
        http_get=_fake_http_get(calls, {"transactions": [{"issuer": "NVDA"}]}),
    )

    imported = source.load()

    parsed = urlparse(calls[0])
    assert parsed.path == "/insider-transactions"
    assert parse_qs(parsed.query)["ticker"] == ["NVDA"]
    assert imported.context_type == "insider_transactions"
    assert imported.payload == {
        "symbol": "NVDA",
        "provider": "finqual",
        "period": "1m",
        "data": {"transactions": [{"issuer": "NVDA"}]},
    }
    assert "secret-key" not in source.source_ref


def test_13f_loads_payload_and_query_shape() -> None:
    """The 13F adapter stores CIK, period, and provider response."""
    calls = []
    source = Finqual13FImportSource(
        "0001067983",
        1,
        api_key="secret-key",
        http_get=_fake_http_get(calls, {"holdings": [{"name": "APPLE INC"}]}),
    )

    imported = source.load()

    parsed = urlparse(calls[0])
    assert parsed.path == "/13f"
    query = parse_qs(parsed.query)
    assert query["cik"] == ["0001067983"]
    assert query["period"] == ["1"]
    assert imported.context_type == "institutional_holdings_13f"
    assert imported.payload == {
        "cik": "0001067983",
        "provider": "finqual",
        "period": 1,
        "data": {"holdings": [{"name": "APPLE INC"}]},
    }
    assert "secret-key" not in source.source_ref


def test_13f_requires_positive_period() -> None:
    """13F periods must be positive."""
    with pytest.raises(ValueError, match="period must be positive"):
        Finqual13FImportSource("0001067983", 0)


def _fake_http_get(calls, response):
    def http_get(url):
        calls.append(url)
        return response

    return http_get
