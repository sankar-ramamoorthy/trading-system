"""Service workflow for human-controlled paper broker execution."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from trading_system.domain.trading.broker_order import (
    BrokerOrder,
    BrokerOrderStatus,
)
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.order_intent import OrderIntentStatus
from trading_system.ports.broker import BrokerClient
from trading_system.ports.repositories import (
    BrokerOrderRepository,
    FillRepository,
    LifecycleEventRepository,
    OrderIntentRepository,
    PositionRepository,
)


@dataclass(frozen=True)
class PaperOrderSyncResult:
    """Result of syncing a paper broker order into local records."""

    broker_order: BrokerOrder
    fill: Fill | None
    position_state: str
    open_quantity: Decimal


class BrokerExecutionService:
    """Coordinates local paper broker submission and fill import."""

    def __init__(
        self,
        *,
        order_intent_repository: OrderIntentRepository,
        position_repository: PositionRepository,
        broker_order_repository: BrokerOrderRepository,
        fill_repository: FillRepository,
        lifecycle_event_repository: LifecycleEventRepository,
        broker_client: BrokerClient,
    ) -> None:
        self._order_intents = order_intent_repository
        self._positions = position_repository
        self._broker_orders = broker_order_repository
        self._fills = fill_repository
        self._lifecycle_events = lifecycle_event_repository
        self._broker_client = broker_client

    def submit_paper_order(
        self,
        order_intent_id: UUID,
        position_id: UUID,
        provider: str = "simulated",
    ) -> BrokerOrder:
        """Submit an existing order intent to a paper broker boundary."""
        if provider != self._broker_client.provider:
            raise ValueError(f"Unsupported paper broker provider: {provider}.")

        order_intent = self._order_intents.get(order_intent_id)
        if order_intent is None:
            raise ValueError("Order intent does not exist.")
        if order_intent.status == OrderIntentStatus.CANCELED:
            raise ValueError("Canceled order intent cannot be submitted to a broker.")

        position = self._positions.get(position_id)
        if position is None:
            raise ValueError("Position does not exist.")
        if position.lifecycle_state != "open":
            raise ValueError("Broker orders require an open local position.")
        if position.trade_plan_id != order_intent.trade_plan_id:
            raise ValueError("Order intent must belong to the same trade plan as the position.")
        if self._broker_orders.get_by_order_intent_id(order_intent.id) is not None:
            raise ValueError("Order intent already has a broker order.")

        submission = self._broker_client.submit_order(order_intent, position)
        broker_order = BrokerOrder(
            order_intent_id=order_intent.id,
            position_id=position.id,
            provider=submission.provider,
            provider_order_id=submission.provider_order_id,
            symbol=order_intent.symbol,
            side=order_intent.side,
            order_type=order_intent.order_type,
            quantity=order_intent.quantity,
            limit_price=order_intent.limit_price,
            stop_price=order_intent.stop_price,
            status=submission.status,
            submitted_at=submission.submitted_at,
            updated_at=submission.updated_at,
        )
        self._broker_orders.add(broker_order)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=broker_order.id,
                entity_type="BrokerOrder",
                event_type="BROKER_ORDER_SUBMITTED",
                note=f"Submitted paper broker order for order intent {order_intent.id}.",
                details={
                    "broker_order_id": str(broker_order.id),
                    "order_intent_id": str(order_intent.id),
                    "position_id": str(position.id),
                    "provider": broker_order.provider,
                    "provider_order_id": broker_order.provider_order_id,
                    "status": broker_order.status.value,
                },
            )
        )
        return broker_order

    def sync_paper_order(
        self,
        broker_order_id: UUID,
        simulated_fill_price: Decimal | None = None,
    ) -> PaperOrderSyncResult:
        """Import a paper broker fill into the local position lifecycle."""
        broker_order = self._broker_orders.get(broker_order_id)
        if broker_order is None:
            raise ValueError("Broker order does not exist.")
        if broker_order.provider != self._broker_client.provider:
            raise ValueError(
                f"Unsupported paper broker provider: {broker_order.provider}."
            )

        existing_fills = self._fills.list_by_broker_order_id(broker_order.id)
        if existing_fills:
            fill = sorted(existing_fills, key=lambda item: item.filled_at)[0]
            position = self._positions.get(broker_order.position_id)
            if position is None:
                raise ValueError("Position does not exist.")
            return PaperOrderSyncResult(
                broker_order=broker_order,
                fill=fill,
                position_state=position.lifecycle_state,
                open_quantity=position.current_quantity,
            )

        if broker_order.status in {
            BrokerOrderStatus.CANCELED,
            BrokerOrderStatus.REJECTED,
        }:
            raise ValueError("Canceled or rejected broker orders cannot be synced as fills.")

        order_intent = self._order_intents.get(broker_order.order_intent_id)
        if order_intent is None:
            raise ValueError("Order intent does not exist.")
        position = self._positions.get(broker_order.position_id)
        if position is None:
            raise ValueError("Position does not exist.")

        synced = self._broker_client.sync_order(
            broker_order.provider_order_id,
            simulated_fill_price=simulated_fill_price,
        )
        if synced.status != BrokerOrderStatus.FILLED or synced.fill_price is None:
            updated = replace(
                broker_order,
                status=synced.status,
                updated_at=synced.updated_at,
            )
            self._broker_orders.update(updated)
            self._lifecycle_events.add(
                LifecycleEvent(
                    entity_id=updated.id,
                    entity_type="BrokerOrder",
                    event_type="BROKER_ORDER_SYNCED",
                    note=f"Synced paper broker order {updated.id}.",
                    details={
                        "broker_order_id": str(updated.id),
                        "order_intent_id": str(updated.order_intent_id),
                        "position_id": str(updated.position_id),
                        "provider": updated.provider,
                        "provider_order_id": updated.provider_order_id,
                        "previous_status": broker_order.status.value,
                        "status": updated.status.value,
                    },
                )
            )
            return PaperOrderSyncResult(
                broker_order=updated,
                fill=None,
                position_state=position.lifecycle_state,
                open_quantity=position.current_quantity,
            )

        was_open = position.lifecycle_state == "open"
        fill = Fill(
            position_id=position.id,
            side=broker_order.side.value,
            quantity=broker_order.quantity,
            price=synced.fill_price,
            order_intent_id=order_intent.id,
            broker_order_id=broker_order.id,
            source=f"broker:{broker_order.provider}",
        )
        position.record_fill(fill)

        updated_order = replace(
            broker_order,
            status=BrokerOrderStatus.FILLED,
            updated_at=synced.updated_at,
        )
        self._broker_orders.update(updated_order)
        self._fills.add(fill)
        self._positions.update(position)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=updated_order.id,
                entity_type="BrokerOrder",
                event_type="BROKER_ORDER_FILLED",
                note=f"Imported paper broker fill {fill.id}.",
                details={
                    "broker_order_id": str(updated_order.id),
                    "fill_id": str(fill.id),
                    "order_intent_id": str(order_intent.id),
                    "position_id": str(position.id),
                    "provider": updated_order.provider,
                    "status": updated_order.status.value,
                    "fill_price": str(fill.price),
                },
            )
        )
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=position.id,
                entity_type="Position",
                event_type="FILL_RECORDED",
                note=f"Recorded broker fill {fill.id}.",
                details={
                    "fill_id": str(fill.id),
                    "side": fill.side,
                    "quantity": str(fill.quantity),
                    "price": str(fill.price),
                    "order_intent_id": str(fill.order_intent_id),
                    "broker_order_id": str(fill.broker_order_id),
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
        return PaperOrderSyncResult(
            broker_order=updated_order,
            fill=fill,
            position_state=position.lifecycle_state,
            open_quantity=position.current_quantity,
        )

    def cancel_paper_order(self, broker_order_id: UUID) -> BrokerOrder:
        """Cancel a submitted simulated paper broker order."""
        broker_order = self._get_mutable_submitted_order(broker_order_id)
        updated_order = replace(
            broker_order,
            status=BrokerOrderStatus.CANCELED,
            updated_at=datetime.now(UTC),
        )
        self._broker_orders.update(updated_order)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=updated_order.id,
                entity_type="BrokerOrder",
                event_type="BROKER_ORDER_CANCELED",
                note=f"Canceled paper broker order {updated_order.id}.",
                details={
                    "broker_order_id": str(updated_order.id),
                    "order_intent_id": str(updated_order.order_intent_id),
                    "position_id": str(updated_order.position_id),
                    "provider": updated_order.provider,
                    "status": updated_order.status.value,
                },
            )
        )
        return updated_order

    def reject_paper_order(self, broker_order_id: UUID, reason: str) -> BrokerOrder:
        """Reject a submitted simulated paper broker order with an audit reason."""
        if not reason.strip():
            raise ValueError("Rejection reason is required.")
        broker_order = self._get_mutable_submitted_order(broker_order_id)
        updated_order = replace(
            broker_order,
            status=BrokerOrderStatus.REJECTED,
            updated_at=datetime.now(UTC),
        )
        self._broker_orders.update(updated_order)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=updated_order.id,
                entity_type="BrokerOrder",
                event_type="BROKER_ORDER_REJECTED",
                note=f"Rejected paper broker order {updated_order.id}.",
                details={
                    "broker_order_id": str(updated_order.id),
                    "order_intent_id": str(updated_order.order_intent_id),
                    "position_id": str(updated_order.position_id),
                    "provider": updated_order.provider,
                    "status": updated_order.status.value,
                    "reason": reason,
                },
            )
        )
        return updated_order

    def _get_mutable_submitted_order(self, broker_order_id: UUID) -> BrokerOrder:
        """Load a broker order that can still be canceled or rejected."""
        broker_order = self._broker_orders.get(broker_order_id)
        if broker_order is None:
            raise ValueError("Broker order does not exist.")
        if broker_order.provider != self._broker_client.provider:
            raise ValueError(
                f"Unsupported paper broker provider: {broker_order.provider}."
            )
        if broker_order.status != BrokerOrderStatus.SUBMITTED:
            raise ValueError("Only submitted broker orders can be canceled or rejected.")
        return broker_order
