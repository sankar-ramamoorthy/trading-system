"""Service workflow for canceling an existing audited order intent."""

from dataclasses import replace
from uuid import UUID

from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.order_intent import OrderIntent, OrderIntentStatus
from trading_system.ports.repositories import (
    LifecycleEventRepository,
    OrderIntentRepository,
)


class CancelOrderIntentService:
    """Coordinates explicit order-intent cancellation within the manual workflow slice."""

    def __init__(
        self,
        order_intent_repository: OrderIntentRepository,
        lifecycle_event_repository: LifecycleEventRepository,
    ) -> None:
        self._order_intents = order_intent_repository
        self._lifecycle_events = lifecycle_event_repository

    def cancel_order_intent(self, order_intent_id: UUID) -> OrderIntent:
        """Persist a canceled order intent and emit a lifecycle event."""
        order_intent = self._order_intents.get(order_intent_id)
        if order_intent is None:
            raise ValueError("Order intent does not exist.")
        if order_intent.status == OrderIntentStatus.CANCELED:
            raise ValueError("Order intent is already canceled.")

        canceled_order_intent = replace(
            order_intent,
            status=OrderIntentStatus.CANCELED,
        )
        self._order_intents.update(canceled_order_intent)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=canceled_order_intent.id,
                entity_type="OrderIntent",
                event_type="ORDER_INTENT_CANCELED",
                note=f"Canceled order intent for trade plan {canceled_order_intent.trade_plan_id}.",
                details={
                    "order_intent_id": str(canceled_order_intent.id),
                    "trade_plan_id": str(canceled_order_intent.trade_plan_id),
                    "status": canceled_order_intent.status.value,
                },
            )
        )
        return canceled_order_intent
