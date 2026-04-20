"""Service workflows for post-trade review creation."""

from uuid import UUID

from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.review import TradeReview
from trading_system.ports.repositories import (
    LifecycleEventRepository,
    PositionRepository,
    TradeReviewRepository,
)


class ReviewService:
    """Coordinates trade review workflows without persistence details."""

    def __init__(
        self,
        position_repository: PositionRepository,
        review_repository: TradeReviewRepository,
        lifecycle_event_repository: LifecycleEventRepository,
    ) -> None:
        self._positions = position_repository
        self._reviews = review_repository
        self._lifecycle_events = lifecycle_event_repository

    def create_trade_review(
        self,
        position_id: UUID,
        summary: str,
        what_went_well: str,
        what_went_poorly: str,
        lessons_learned: list[str] | None = None,
        follow_up_actions: list[str] | None = None,
        rating: int | None = None,
    ) -> TradeReview:
        """Create one immutable manual review for a closed position."""
        position = self._positions.get(position_id)
        if position is None:
            raise ValueError("Position does not exist.")
        if position.lifecycle_state != "closed":
            raise ValueError("Trade review requires a closed position.")
        if self._reviews.get_by_position_id(position_id) is not None:
            raise ValueError("Trade review already exists for this position.")

        review = TradeReview(
            position_id=position_id,
            summary=summary,
            what_went_well=what_went_well,
            what_went_poorly=what_went_poorly,
            lessons_learned=list(lessons_learned or []),
            follow_up_actions=list(follow_up_actions or []),
            rating=rating,
        )
        self._reviews.add(review)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=review.id,
                entity_type="TradeReview",
                event_type="TRADE_REVIEW_CREATED",
                note=f"Created trade review for position {position_id}.",
                details={
                    "review_id": str(review.id),
                    "position_id": str(position_id),
                    "reviewed_at": review.reviewed_at.isoformat(),
                },
            )
        )
        return review
