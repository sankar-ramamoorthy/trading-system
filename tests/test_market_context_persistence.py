"""Tests for market context JSON persistence and file import."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.infrastructure.json.market_context_source import (
    JsonMarketContextImportSource,
)
from trading_system.infrastructure.json.repositories import build_json_repositories


def test_market_context_snapshot_survives_repository_reload(tmp_path) -> None:
    """Market context snapshots round-trip through the local JSON store."""
    store_path = tmp_path / "store.json"
    instrument_id = uuid4()
    target_id = uuid4()
    snapshot = MarketContextSnapshot(
        instrument_id=instrument_id,
        target_type="TradePlan",
        target_id=target_id,
        context_type="price_snapshot",
        source="local-file",
        source_ref="context.json",
        observed_at=datetime(2026, 4, 26, 16, 0, tzinfo=UTC),
        payload={"symbol": "AAPL", "last": "185.25"},
    )

    build_json_repositories(store_path).market_context_snapshots.add(snapshot)
    reloaded = build_json_repositories(store_path).market_context_snapshots

    assert reloaded.get(snapshot.id) == snapshot
    assert reloaded.list_by_instrument_id(instrument_id) == [snapshot]
    assert reloaded.list_by_target("TradePlan", target_id) == [snapshot]


def test_market_context_import_source_loads_valid_json(tmp_path) -> None:
    """The local file adapter loads the accepted import envelope."""
    import_path = tmp_path / "context.json"
    import_path.write_text(
        """
        {
          "context_type": "price_snapshot",
          "observed_at": "2026-04-26T16:00:00+00:00",
          "payload": {
            "symbol": "AAPL",
            "last": "185.25"
          }
        }
        """,
        encoding="utf-8",
    )

    imported = JsonMarketContextImportSource(import_path).load()

    assert imported.context_type == "price_snapshot"
    assert imported.observed_at == datetime(2026, 4, 26, 16, 0, tzinfo=UTC)
    assert imported.payload == {"symbol": "AAPL", "last": "185.25"}


def test_market_context_import_source_rejects_invalid_json(tmp_path) -> None:
    """Invalid context import files report clear validation errors."""
    import_path = tmp_path / "context.json"
    import_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON"):
        JsonMarketContextImportSource(import_path).load()


def test_market_context_import_source_requires_payload_object(tmp_path) -> None:
    """Context import payloads must stay structured."""
    import_path = tmp_path / "context.json"
    import_path.write_text(
        """
        {
          "context_type": "price_snapshot",
          "observed_at": "2026-04-26T16:00:00+00:00",
          "payload": "AAPL 185.25"
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="payload"):
        JsonMarketContextImportSource(import_path).load()
