"""CLI tests for yfinance-backed daily OHLCV ingestion."""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from typer.testing import CliRunner

from trading_system.app.cli import app
from trading_system.infrastructure.json.repositories import build_json_repositories
from trading_system.services.trade_planning_service import TradePlanningService


runner = CliRunner()


def test_fetch_market_data_to_target_and_show_snapshot(tmp_path, monkeypatch) -> None:
    """The CLI fetches daily OHLCV data and stores it as linked context."""
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    trade_plan_id = _create_plan(repositories)
    frame = _Frame(
        columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"],
        rows=[
            (
                datetime(2026, 4, 1, 0, 0),
                {
                    "Open": 100.0,
                    "High": 105.0,
                    "Low": 99.5,
                    "Close": 104.0,
                    "Adj Close": 103.5,
                    "Volume": 1000,
                },
            ),
            (
                datetime(2026, 4, 2, 0, 0),
                {
                    "Open": 104.0,
                    "High": 106.0,
                    "Low": 101.0,
                    "Close": 105.5,
                    "Adj Close": 105.0,
                    "Volume": 1200,
                },
            ),
        ],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.market_data_source.import_module",
        lambda name: SimpleNamespace(download=lambda *args, **kwargs: frame),
    )

    result = runner.invoke(
        app,
        [
            "fetch-market-data",
            "AAPL",
            "--start",
            "2026-04-01",
            "--end",
            "2026-04-03",
            "--target-type",
            "trade-plan",
            "--target-id",
            str(trade_plan_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    snapshot_id = _lines(result.output)[0].split(": ")[1]
    assert "context_type: daily_ohlcv" in result.output
    assert "source: yfinance" in result.output
    assert "target_type: TradePlan" in result.output

    detail = runner.invoke(
        app,
        ["show-trade-plan", str(trade_plan_id)],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    shown = runner.invoke(
        app,
        ["show-context", snapshot_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )
    listed = runner.invoke(
        app,
        ["list-context", "--context-type", "daily_ohlcv", "--source", "yfinance"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert detail.exit_code == 0
    assert f"market_context_snapshot_id: {snapshot_id}" in detail.output
    assert shown.exit_code == 0
    assert '"provider": "yfinance"' in shown.output
    assert '"end_exclusive": "2026-04-03"' in shown.output
    assert listed.exit_code == 0
    assert snapshot_id in listed.output


def test_fetch_market_data_accepts_explicit_yfinance_provider(tmp_path, monkeypatch) -> None:
    """The CLI can select yfinance explicitly without changing snapshot shape."""
    store_path = tmp_path / "store.json"
    instrument_id = uuid4()
    frame = _Frame(
        columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"],
        rows=[
            (
                datetime(2026, 4, 1, 0, 0),
                {
                    "Open": 100.0,
                    "High": 105.0,
                    "Low": 99.5,
                    "Close": 104.0,
                    "Adj Close": 103.5,
                    "Volume": 1000,
                },
            ),
        ],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.market_data_source.import_module",
        lambda name: SimpleNamespace(download=lambda *args, **kwargs: frame),
    )

    result = runner.invoke(
        app,
        [
            "fetch-market-data",
            "aapl",
            "--provider",
            "yfinance",
            "--start",
            "2026-04-01",
            "--end",
            "2026-04-03",
            "--instrument-id",
            str(instrument_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code == 0
    assert "context_type: daily_ohlcv" in result.output
    assert "source: yfinance" in result.output
    assert "instrument_id: " + str(instrument_id) in result.output


def test_fetch_market_data_rejects_unsupported_provider(tmp_path) -> None:
    """Unsupported provider names fail before a snapshot is created."""
    store_path = tmp_path / "store.json"

    result = runner.invoke(
        app,
        [
            "fetch-market-data",
            "AAPL",
            "--provider",
            "iex",
            "--start",
            "2026-04-01",
            "--end",
            "2026-04-03",
            "--instrument-id",
            str(uuid4()),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "Market data provider is not supported." in result.output


def test_fetch_market_data_accepts_massive_provider(tmp_path, monkeypatch) -> None:
    """The CLI can select Massive.com and store provider-backed snapshots."""
    store_path = tmp_path / "store.json"
    instrument_id = uuid4()
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.market_data_source.import_module",
        lambda name: SimpleNamespace(
            RESTClient=lambda api_key: _MassiveClient(
                [{"t": 1775001600000, "o": 1, "h": 2, "l": 1, "c": 2, "v": 100}]
            )
        ),
    )

    result = runner.invoke(
        app,
        [
            "fetch-market-data",
            "aapl",
            "--provider",
            "massive",
            "--start",
            "2026-04-01",
            "--end",
            "2026-04-03",
            "--instrument-id",
            str(instrument_id),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path), "MASSIVE_API_KEY": "test-key"},
    )

    assert result.exit_code == 0
    snapshot_id = _lines(result.output)[0].split(": ")[1]
    assert "context_type: daily_ohlcv" in result.output
    assert "source: massive" in result.output
    assert "instrument_id: " + str(instrument_id) in result.output

    shown = runner.invoke(
        app,
        ["show-context", snapshot_id],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert shown.exit_code == 0
    assert '"provider": "massive"' in shown.output
    assert '"end": "2026-04-03"' in shown.output


def test_fetch_market_data_massive_requires_api_key(tmp_path, monkeypatch) -> None:
    """Missing Massive credentials fail before a snapshot is stored."""
    store_path = tmp_path / "store.json"
    monkeypatch.setattr(
        "trading_system.infrastructure.massive.market_data_source.import_module",
        lambda name: SimpleNamespace(RESTClient=lambda api_key: _MassiveClient([])),
    )

    result = runner.invoke(
        app,
        [
            "fetch-market-data",
            "AAPL",
            "--provider",
            "massive",
            "--start",
            "2026-04-01",
            "--end",
            "2026-04-03",
            "--instrument-id",
            str(uuid4()),
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "MASSIVE_API_KEY is required" in result.output

    listed = runner.invoke(
        app,
        ["list-context"],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert listed.exit_code == 0
    assert "No market context snapshots found." in listed.output


def test_fetch_market_data_requires_instrument_or_target(tmp_path, monkeypatch) -> None:
    """The CLI keeps existing instrument/target linking rules."""
    store_path = tmp_path / "store.json"
    frame = _Frame(
        columns=["Open", "High", "Low", "Close", "Adj Close", "Volume"],
        rows=[(datetime(2026, 4, 1, 0, 0), {"Open": 1, "High": 2, "Low": 1, "Close": 2, "Adj Close": 2, "Volume": 100})],
    )
    monkeypatch.setattr(
        "trading_system.infrastructure.yfinance.market_data_source.import_module",
        lambda name: SimpleNamespace(download=lambda *args, **kwargs: frame),
    )

    result = runner.invoke(
        app,
        [
            "fetch-market-data",
            "AAPL",
            "--start",
            "2026-04-01",
            "--end",
            "2026-04-03",
        ],
        env={"TRADING_SYSTEM_STORE_PATH": str(store_path)},
    )

    assert result.exit_code != 0
    assert "Instrument id is required when no context target is provided." in result.output


def _create_plan(repositories):
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    idea = planning.create_trade_idea(
        instrument_id=uuid4(),
        playbook_id=uuid4(),
        purpose="swing",
        direction="long",
        horizon="days_to_weeks",
    )
    thesis = planning.create_trade_thesis(
        trade_idea_id=idea.id,
        reasoning="Setup has a clear catalyst.",
    )
    plan = planning.create_trade_plan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Breakout confirmation.",
        invalidation="Close below setup low.",
        risk_model="Defined stop and max loss.",
    )
    return planning.approve_trade_plan(plan.id).id


def _lines(output: str) -> list[str]:
    return output.rstrip().splitlines()


class _Frame:
    def __init__(self, *, columns: list[str], rows: list[tuple[object, dict[str, object]]]) -> None:
        self.columns = columns
        self._rows = rows

    @property
    def empty(self) -> bool:
        return not self._rows

    def iterrows(self):
        return iter(self._rows)


class _MassiveClient:
    def __init__(self, bars):
        self._bars = bars

    def list_aggs(self, **kwargs):
        return self._bars
