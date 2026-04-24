"""Service workflows for manual fill recording."""

from decimal import Decimal
from uuid import UUID

from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.ports.repositories import (
    FillRepository,
    LifecycleEventRepository,
    OrderIntentRepository,
    PositionRepository,
)


class FillService:
    """Coordinates manual fill recording for open positions."""

    def __init__(
        self,
        position_repository: PositionRepository,
        fill_repository: FillRepository,
        lifecycle_event_repository: LifecycleEventRepository,
        order_intent_repository: OrderIntentRepository | None = None,
    ) -> None:
        self._positions = position_repository
        self._fills = fill_repository
        self._lifecycle_events = lifecycle_event_repository
        self._order_intents = order_intent_repository

    def record_manual_fill(
        self,
        position_id: UUID,
        side: str,
        quantity: Decimal,
        price: Decimal,
        notes: str | None = None,
        order_intent_id: UUID | None = None,
    ) -> Fill:
        """Record a manual fill, update position state, and emit an audit event."""
        position = self._positions.get(position_id)
        if position is None:
            raise ValueError("Position does not exist.")
        if order_intent_id is not None:
            if self._order_intents is None:
                raise ValueError("Order intent repository is not configured.")
            order_intent = self._order_intents.get(order_intent_id)
            if order_intent is None:
                raise ValueError("Order intent does not exist.")
            if order_intent.trade_plan_id != position.trade_plan_id:
                raise ValueError("Order intent must belong to the same trade plan as the position.")

        was_open = position.lifecycle_state == "open"
        fill = Fill(
            position_id=position.id,
            side=side,
            quantity=quantity,
            price=price,
            order_intent_id=order_intent_id,
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
                    "order_intent_id": None
                    if fill.order_intent_id is None
                    else str(fill.order_intent_id),
                    "filled_at": fill.filled_at.isoformat(),
                    "source": fill.source,
                },
            )
        )
        if was_open and position.lifecycle_state == "closed":
            self._lifecycle_events.add(
                LifecycleEvent(
                    entity_id=position.id,
                    entity_type="Position",
                    event_type="POSITION_CLOSED",
                    note=f"Closed position from fill {fill.id}.",
                    details={
                        "position_id": str(position.id),
                        "closed_at": position.closed_at.isoformat()
                        if position.closed_at
                        else None,
                        "closing_fill_id": str(fill.id),
                        "current_quantity": str(position.current_quantity),
                        "close_reason": position.close_reason,
                    },
                )
            )
        return fill
