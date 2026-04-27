"""Tests for manual trade review creation."""

from decimal import Decimal
from uuid import uuid4

import pytest

from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.position import Position
from trading_system.infrastructure.memory.repositories import (
    InMemoryLifecycleEventRepository,
    InMemoryPositionRepository,
    InMemoryTradeReviewRepository,
)
from trading_system.services.review_service import ReviewService


def test_create_trade_review_for_closed_position() -> None:
    """A closed position can receive one manual trade review."""
    positions, reviews, lifecycle_events, service = _review_service()
    position = _closed_position()
    positions.add(position)

    review = service.create_trade_review(
        position_id=position.id,
        summary="Followed the plan.",
        what_went_well="Entry and risk were clear.",
        what_went_poorly="Exit was late.",
        lessons_learned=["Define exit criteria earlier."],
        follow_up_actions=["Add exit checklist."],
        tags=["Risk Management", "missed_exit", "risk-management"],
        rating=4,
        process_score=5,
        setup_quality=4,
        execution_quality=3,
        exit_quality=2,
    )

    assert review.position_id == position.id
    assert review.summary == "Followed the plan."
    assert review.what_went_well == "Entry and risk were clear."
    assert review.what_went_poorly == "Exit was late."
    assert review.lessons_learned == ["Define exit criteria earlier."]
    assert review.follow_up_actions == ["Add exit checklist."]
    assert review.tags == ["risk-management", "missed-exit"]
    assert review.rating == 4
    assert review.process_score == 5
    assert review.setup_quality == 4
    assert review.execution_quality == 3
    assert review.exit_quality == 2
    assert review.reviewed_at is not None
    assert reviews.get_by_position_id(position.id) == review

    events = list(lifecycle_events.items.values())
    assert len(events) == 1
    assert events[0].event_type == "TRADE_REVIEW_CREATED"
    assert events[0].details["review_id"] == str(review.id)
    assert events[0].details["position_id"] == str(position.id)


def test_reject_review_for_open_position() -> None:
    """Open positions cannot be reviewed."""
    positions, reviews, lifecycle_events, service = _review_service()
    position = _position()
    positions.add(position)

    with pytest.raises(ValueError, match="closed position"):
        service.create_trade_review(
            position_id=position.id,
            summary="Too early.",
            what_went_well="",
            what_went_poorly="",
        )

    assert reviews.get_by_position_id(position.id) is None
    assert len(lifecycle_events.items) == 0


def test_reject_review_for_missing_position() -> None:
    """Review creation requires an existing position."""
    _, reviews, lifecycle_events, service = _review_service()
    position_id = uuid4()

    with pytest.raises(ValueError, match="Position does not exist"):
        service.create_trade_review(
            position_id=position_id,
            summary="Missing.",
            what_went_well="",
            what_went_poorly="",
        )

    assert reviews.get_by_position_id(position_id) is None
    assert len(lifecycle_events.items) == 0


def test_reject_duplicate_review_for_same_position() -> None:
    """Milestone 1 allows only one review per position."""
    positions, reviews, lifecycle_events, service = _review_service()
    position = _closed_position()
    positions.add(position)
    service.create_trade_review(
        position_id=position.id,
        summary="First review.",
        what_went_well="Plan followed.",
        what_went_poorly="Exit late.",
    )

    with pytest.raises(ValueError, match="already exists"):
        service.create_trade_review(
            position_id=position.id,
            summary="Second review.",
            what_went_well="",
            what_went_poorly="",
        )

    assert len(reviews.items) == 1
    assert len(lifecycle_events.items) == 1


def test_reject_empty_review_tag() -> None:
    """Review tags must normalize to non-empty slugs."""
    positions, reviews, lifecycle_events, service = _review_service()
    position = _closed_position()
    positions.add(position)

    with pytest.raises(ValueError, match="Review tags cannot be empty"):
        service.create_trade_review(
            position_id=position.id,
            summary="Tagged review.",
            what_went_well="Plan followed.",
            what_went_poorly="Exit late.",
            tags=["  "],
        )

    assert reviews.get_by_position_id(position.id) is None
    assert len(lifecycle_events.items) == 0


def test_reject_review_quality_score_outside_one_to_five() -> None:
    """Review quality scores must stay on the 1-5 scale."""
    positions, reviews, lifecycle_events, service = _review_service()
    position = _closed_position()
    positions.add(position)

    with pytest.raises(ValueError, match="process_score must be between 1 and 5"):
        service.create_trade_review(
            position_id=position.id,
            summary="Scored review.",
            what_went_well="Plan followed.",
            what_went_poorly="Exit late.",
            process_score=0,
        )

    assert reviews.get_by_position_id(position.id) is None
    assert len(lifecycle_events.items) == 0


def test_full_closed_position_flow_can_create_review() -> None:
    """A position closed by fills can be reviewed."""
    positions, reviews, _, service = _review_service()
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

    review = service.create_trade_review(
        position_id=position.id,
        summary="Completed trade reviewed.",
        what_went_well="Process was followed.",
        what_went_poorly="Could improve exit timing.",
    )

    assert position.lifecycle_state == "closed"
    assert reviews.get_by_position_id(position.id) == review


def _review_service() -> tuple[
    InMemoryPositionRepository,
    InMemoryTradeReviewRepository,
    InMemoryLifecycleEventRepository,
    ReviewService,
]:
    positions = InMemoryPositionRepository()
    reviews = InMemoryTradeReviewRepository()
    lifecycle_events = InMemoryLifecycleEventRepository()
    service = ReviewService(positions, reviews, lifecycle_events)
    return positions, reviews, lifecycle_events, service


def _closed_position() -> Position:
    position = _position()
    position.lifecycle_state = "closed"
    return position


def _position() -> Position:
    return Position(
        trade_plan_id=uuid4(),
        instrument_id=uuid4(),
        purpose="swing",
    )
