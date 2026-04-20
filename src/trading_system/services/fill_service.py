"""Service workflows for manual fill recording."""

from decimal import Decimal
from uuid import UUID

from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.ports.repositories import (
    FillRepository,
    LifecycleEventRepository,
    PositionRepository,
)


class FillService:
    """Coordinates manual fill recording for open positions."""

    def __init__(
        self,
        position_repository: PositionRepository,
        fill_repository: FillRepository,
        lifecycle_event_repository: LifecycleEventRepository,
    ) -> None:
        self._positions = position_repository
        self._fills = fill_repository
        self._lifecycle_events = lifecycle_event_repository

    def record_manual_fill(
        self,
        position_id: UUID,
        side: str,
        quantity: Decimal,
        price: Decimal,
        notes: str | None = None,
    ) -> Fill:
        """Record a manual fill, update position state, and emit an audit event."""
        position = self._positions.get(position_id)
        if position is None:
            raise ValueError("Position does not exist.")

        fill = Fill(
            position_id=position.id,
            side=side,
            quantity=quantity,
            price=price,
            notes=notes,
        )
        position.record_fill(fill)

        self._fills.add(fill)
        self._positions.update(position)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=position.id,
                entity_type="Position",
                event_type="FILL_RECORDED",
                note=f"Recorded manual fill {fill.id}.",
                details={
                    "fill_id": str(fill.id),
                    "side": fill.side,
                    "quantity": str(fill.quantity),
                    "price": str(fill.price),
                    "filled_at": fill.filled_at.isoformat(),
                    "source": fill.source,
                },
            )
        )
        return fill
