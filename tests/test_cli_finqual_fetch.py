"""CLI tests for Finqual-backed context ingestion."""

from uuid import uuid4

from typer.testing import CliRunner

from trading_system.app.cli import app


runner = CliRunner()


def test_fetch_financial_statement_stores_finqual_snapshot(tmp_path, monkeypatch) -> None:
    """The CLI stores Finqual financial statements as market context."""
    store_path = tmp_path / "store.json"
    instrument_id = uuid4()
    monkeypatch.setattr(
        "trading_system.infrastructure.finqual.context_sources._get_json",
        lambda url: {"items": [{"revenue": 1}]},
    )

    result = runner.invoke(
        app,
        [
            "fetch-financial-statement",
            "aapl",
            "--statement",
            "income-statement",
            "--start",
            "2024",
            "--end",
            "2025",
            "--instrument-id",
            str(instrument_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path), "FINQUAL_API_KEY": "test-key"},
    )

    assert result.exit_code == 0
    snapshot_id = _lines(result.output)[0].split(": ")[1]
    assert "context_type: financial_statement" in result.output
    assert "source: finqual" in result.output
    assert "instrument_id: " + str(instrument_id) in result.output

    shown = runner.invoke(
        app,
        ["show-context", snapshot_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    listed = runner.invoke(
        app,
        ["list-context", "--context-type", "financial_statement", "--source", "finqual"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert shown.exit_code == 0
    assert '"provider": "finqual"' in shown.output
    assert '"statement": "income-statement"' in shown.output
    assert "test-key" not in shown.output
    assert listed.exit_code == 0
    assert snapshot_id in listed.output


def test_fetch_financial_statement_requires_finqual_key(tmp_path, monkeypatch) -> None:
    """Missing Finqual credentials fail before a snapshot is stored."""
    import trading_system.infrastructure.local_secret_vault as secret_vault

    store_path = tmp_path / "store.json"
    monkeypatch.setattr(secret_vault, "DEFAULT_VAULT_PATH", tmp_path / "keys.enc")
    monkeypatch.delenv("FINQUAL_API_KEY", raising=False)
    monkeypatch.setattr(
        "trading_system.infrastructure.finqual.context_sources._get_json",
        lambda url: {"items": []},
    )

    result = runner.invoke(
        app,
        [
            "fetch-financial-statement",
            "AAPL",
            "--statement",
            "income-statement",
            "--start",
            "2024",
            "--end",
            "2025",
            "--instrument-id",
            str(uuid4()),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "FINQUAL_API_KEY is required" in result.output

    listed = runner.invoke(
        app,
        ["list-context"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert listed.exit_code == 0
    assert "No market context snapshots found." in listed.output


def test_fetch_insider_transactions_stores_finqual_snapshot(tmp_path, monkeypatch) -> None:
    """The CLI stores Finqual insider transactions as market context."""
    store_path = tmp_path / "store.json"
    instrument_id = uuid4()
    monkeypatch.setattr(
        "trading_system.infrastructure.finqual.context_sources._get_json",
        lambda url: {"transactions": [{"ticker": "NVDA"}]},
    )

    result = runner.invoke(
        app,
        [
            "fetch-insider-transactions",
            "nvda",
            "--period",
            "1m",
            "--instrument-id",
            str(instrument_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path), "FINQUAL_API_KEY": "test-key"},
    )

    assert result.exit_code == 0
    snapshot_id = _lines(result.output)[0].split(": ")[1]
    assert "context_type: insider_transactions" in result.output
    assert "source: finqual" in result.output

    shown = runner.invoke(
        app,
        ["show-context", snapshot_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert shown.exit_code == 0
    assert '"period": "1m"' in shown.output
    assert '"transactions":' in shown.output
    assert "test-key" not in shown.output


def test_fetch_13f_stores_finqual_snapshot_with_explicit_instrument(
    tmp_path,
    monkeypatch,
) -> None:
    """CIK-based 13F imports store context when an instrument is supplied."""
    store_path = tmp_path / "store.json"
    instrument_id = uuid4()
    monkeypatch.setattr(
        "trading_system.infrastructure.finqual.context_sources._get_json",
        lambda url: {"holdings": [{"issuer": "APPLE INC"}]},
    )

    result = runner.invoke(
        app,
        [
            "fetch-13f",
            "0001067983",
            "--period",
            "1",
            "--instrument-id",
            str(instrument_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path), "FINQUAL_API_KEY": "test-key"},
    )

    assert result.exit_code == 0
    snapshot_id = _lines(result.output)[0].split(": ")[1]
    assert "context_type: institutional_holdings_13f" in result.output
    assert "source: finqual" in result.output
    assert "instrument_id: " + str(instrument_id) in result.output

    shown = runner.invoke(
        app,
        ["show-context", snapshot_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert shown.exit_code == 0
    assert '"cik": "0001067983"' in shown.output
    assert '"holdings":' in shown.output
    assert "test-key" not in shown.output


def test_fetch_13f_requires_instrument_or_target(tmp_path, monkeypatch) -> None:
    """CIK-only context cannot bypass the snapshot instrument boundary."""
    store_path = tmp_path / "store.json"
    monkeypatch.setattr(
        "trading_system.infrastructure.finqual.context_sources._get_json",
        lambda url: {"holdings": []},
    )

    result = runner.invoke(
        app,
        ["fetch-13f", "0001067983", "--period", "1"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path), "FINQUAL_API_KEY": "test-key"},
    )

    assert result.exit_code != 0
    assert "Instrument id is required when no context target is provided" in result.output


def test_fetch_finqual_context_rejects_unsupported_provider(tmp_path) -> None:
    """Unsupported provider names fail before a snapshot is created."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        [
            "fetch-insider-transactions",
            "AAPL",
            "--period",
            "1m",
            "--provider",
            "massive",
            "--instrument-id",
            str(uuid4()),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path), "FINQUAL_API_KEY": "test-key"},
    )

    assert result.exit_code != 0
    assert "Finqual provider is not supported." in result.output


def _lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.strip()]
