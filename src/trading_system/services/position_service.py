"""Service stubs for position lifecycle workflows."""

from trading_system.domain.trading.position import Position


class PositionService:
    """Coordinates position workflows without persistence details."""

    def open_position_from_plan(self, trade_plan_id: object) -> Position:
        """Open a position from an approved trade plan."""
        raise NotImplementedError("Position opening workflow is not implemented yet.")
