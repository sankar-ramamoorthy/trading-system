"""Service stubs for trade review workflows."""

from trading_system.domain.trading.review import TradeReview


class ReviewService:
    """Coordinates trade review workflows without persistence details."""

    def review_trade(self, position_id: object) -> TradeReview:
        """Create a post-trade review for a position."""
        raise NotImplementedError("Trade review workflow is not implemented yet.")
