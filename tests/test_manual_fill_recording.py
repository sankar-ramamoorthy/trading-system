"""Tests for manual fill recording on open positions."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.position import Position
from trading_system.infrastructure.memory.repositories import (
    InMemoryFillRepository,
    InMemoryLifecycleEventRepository,
    InMemoryPositionRepository,
)
from trading_system.services.fill_service import FillService


def test_record_first_fill_on_open_position() -> None:
    """A first buy fill creates open exposure and average entry."""
    position = _position()
    fill = Fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
    )

    position.record_fill(fill)

    assert position.total_bought_quantity == Decimal("100")
    assert position.total_sold_quantity == Decimal("0")
    assert position.current_quantity == Decimal("100")
    assert position.average_entry_price == Decimal("25.50")


def test_record_second_fill_recomputes_weighted_average_entry() -> None:
    """Additional buy fills update the weighted average entry price."""
    position = _position()
    position.record_fill(
        Fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("10"),
        )
    )

    position.record_fill(
        Fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("50"),
            price=Decimal("16"),
        )
    )

    assert position.total_bought_quantity == Decimal("150")
    assert position.current_quantity == Decimal("150")
    assert position.average_entry_price == Decimal("12")


def test_record_partial_reducing_fill() -> None:
    """A sell fill reduces open quantity without changing entry basis."""
    position = _position()
    position.record_fill(
        Fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("20"),
        )
    )

    position.record_fill(
        Fill(
            position_id=position.id,
            side="sell",
            quantity=Decimal("40"),
            price=Decimal("22"),
        )
    )

    assert position.total_bought_quantity == Decimal("100")
    assert position.total_sold_quantity == Decimal("40")
    assert position.current_quantity == Decimal("60")
    assert position.average_entry_price == Decimal("20")
    assert position.lifecycle_state == "open"
    assert position.closed_at is None


def test_reducing_fill_to_zero_closes_position() -> None:
    """A reducing fill that brings open quantity to zero closes the position."""
    position = _position()
    position.record_fill(
        Fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("20"),
        )
    )
    closing_fill = Fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("22"),
    )

    position.record_fill(closing_fill)

    assert position.lifecycle_state == "closed"
    assert position.current_quantity == Decimal("0")
    assert position.average_entry_price is None
    assert position.closed_at == closing_fill.filled_at
    assert position.closing_fill_id == closing_fill.id
    assert position.close_reason == "fills_completed"


def test_further_fill_after_close_is_rejected() -> None:
    """A position cannot be filled again after fills close it."""
    position = _position()
    position.record_fill(
        Fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("20"),
        )
    )
    position.record_fill(
        Fill(
            position_id=position.id,
            side="sell",
            quantity=Decimal("100"),
            price=Decimal("22"),
        )
    )

    with pytest.raises(ValueError, match="closed position"):
        position.record_fill(
            Fill(
                position_id=position.id,
                side="buy",
                quantity=Decimal("10"),
                price=Decimal("21"),
            )
        )


def test_reject_oversell() -> None:
    """Reducing fills cannot exceed current open quantity."""
    position = _position()
    position.record_fill(
        Fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("20"),
        )
    )

    with pytest.raises(ValueError, match="cannot exceed"):
        position.record_fill(
            Fill(
                position_id=position.id,
                side="sell",
                quantity=Decimal("120"),
                price=Decimal("22"),
            )
        )

    assert position.current_quantity == Decimal("100")
    assert position.total_sold_quantity == Decimal("0")


def test_reject_fill_on_closed_position() -> None:
    """Closed positions cannot receive manual fills."""
    position = _position(lifecycle_state="closed")

    with pytest.raises(ValueError, match="closed position"):
        position.record_fill(
            Fill(
                position_id=position.id,
                side="buy",
                quantity=Decimal("100"),
                price=Decimal("20"),
            )
        )


def test_reject_non_positive_quantity() -> None:
    """Fill quantity must be positive."""
    position = _position()

    with pytest.raises(ValueError, match="quantity must be positive"):
        position.record_fill(
            Fill(
                position_id=position.id,
                side="buy",
                quantity=Decimal("0"),
                price=Decimal("20"),
            )
        )


def test_reject_non_positive_price() -> None:
    """Fill price must be positive."""
    position = _position()

    with pytest.raises(ValueError, match="price must be positive"):
        position.record_fill(
            Fill(
                position_id=position.id,
                side="buy",
                quantity=Decimal("100"),
                price=Decimal("0"),
            )
        )


def test_reject_invalid_fill_side() -> None:
    """Fill side must be valid for the supported long-position context."""
    position = _position()

    with pytest.raises(ValueError, match="side must be 'buy' or 'sell'"):
        position.record_fill(
            Fill(
                position_id=position.id,
                side="hold",
                quantity=Decimal("100"),
                price=Decimal("20"),
            )
        )


def test_record_manual_fill_service_persists_updated_position_and_event() -> None:
    """The fill service persists fill, position state, and audit event."""
    positions = InMemoryPositionRepository()
    fills = InMemoryFillRepository()
    lifecycle_events = InMemoryLifecycleEventRepository()
    position = _position()
    positions.add(position)
    service = FillService(positions, fills, lifecycle_events)

    fill = service.record_manual_fill(
        position_id=position.id,
        side="buy",
        quantity=Decimal("100"),
        price=Decimal("25.50"),
        notes="Manual entry.",
    )

    persisted_position = positions.get(position.id)
    events = list(lifecycle_events.items.values())
    assert fills.items[fill.id] == fill
    assert persisted_position is not None
    assert persisted_position.current_quantity == Decimal("100")
    assert persisted_position.average_entry_price == Decimal("25.50")
    assert len(events) == 1
    assert events[0].event_type == "FILL_RECORDED"
    assert events[0].details["fill_id"] == str(fill.id)
    assert events[0].details["quantity"] == "100"
    assert events[0].details["price"] == "25.50"


def test_record_manual_fill_service_persists_closing_transition() -> None:
    """The fill service persists closed position state and audit events."""
    positions = InMemoryPositionRepository()
    fills = InMemoryFillRepository()
    lifecycle_events = InMemoryLifecycleEventRepository()
    position = _position()
    position.record_fill(
        Fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("20"),
        )
    )
    positions.add(position)
    service = FillService(positions, fills, lifecycle_events)

    closing_fill = service.record_manual_fill(
        position_id=position.id,
        side="sell",
        quantity=Decimal("100"),
        price=Decimal("22"),
    )

    persisted_position = positions.get(position.id)
    events = list(lifecycle_events.items.values())
    assert persisted_position is not None
    assert persisted_position.lifecycle_state == "closed"
    assert persisted_position.closed_at == closing_fill.filled_at
    assert persisted_position.closing_fill_id == closing_fill.id
    assert persisted_position.current_quantity == Decimal("0")
    assert len(events) == 2
    assert [event.event_type for event in events] == [
        "FILL_RECORDED",
        "POSITION_CLOSED",
    ]
    close_event = events[1]
    assert close_event.details["position_id"] == str(position.id)
    assert close_event.details["closing_fill_id"] == str(closing_fill.id)
    assert close_event.details["current_quantity"] == "0"


def test_post_close_fill_attempt_does_not_persist_invalid_state() -> None:
    """The service rejects fills after closure without adding records."""
    positions = InMemoryPositionRepository()
    fills = InMemoryFillRepository()
    lifecycle_events = InMemoryLifecycleEventRepository()
    position = _position()
    position.record_fill(
        Fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("100"),
            price=Decimal("20"),
        )
    )
    position.record_fill(
        Fill(
            position_id=position.id,
            side="sell",
            quantity=Decimal("100"),
            price=Decimal("22"),
        )
    )
    positions.add(position)
    service = FillService(positions, fills, lifecycle_events)

    with pytest.raises(ValueError, match="closed position"):
        service.record_manual_fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("10"),
            price=Decimal("21"),
        )

    persisted_position = positions.get(position.id)
    assert persisted_position is not None
    assert persisted_position.lifecycle_state == "closed"
    assert len(fills.items) == 0
    assert len(lifecycle_events.items) == 0


def test_invalid_manual_fill_service_does_not_persist_bad_state() -> None:
    """Invalid fills are rejected before fill or event persistence."""
    positions = InMemoryPositionRepository()
    fills = InMemoryFillRepository()
    lifecycle_events = InMemoryLifecycleEventRepository()
    position = _position()
    positions.add(position)
    service = FillService(positions, fills, lifecycle_events)

    with pytest.raises(ValueError, match="quantity must be positive"):
        service.record_manual_fill(
            position_id=position.id,
            side="buy",
            quantity=Decimal("0"),
            price=Decimal("25.50"),
        )

    persisted_position = positions.get(position.id)
    assert persisted_position is not None
    assert persisted_position.current_quantity == Decimal("0")
    assert len(fills.items) == 0
    assert len(lifecycle_events.items) == 0


def _position(
    lifecycle_state: str = "open",
    position_id: UUID | None = None,
) -> Position:
    return Position(
        id=position_id or uuid4(),
        trade_plan_id=uuid4(),
        instrument_id=uuid4(),
        purpose="swing",
        lifecycle_state=lifecycle_state,
    )
