"""Read-only workflows for local broker-order retrieval."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from trading_system.domain.trading.broker_order import BrokerOrder, BrokerOrderStatus
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.order_intent import OrderIntent
from trading_system.domain.trading.position import Position
from trading_system.ports.repositories import (
    BrokerOrderRepository,
    FillRepository,
    OrderIntentRepository,
    PositionRepository,
)


@dataclass(frozen=True)
class BrokerOrderDetail:
    """Composite read model for inspecting one broker order."""

    broker_order: BrokerOrder
    order_intent: OrderIntent | None
    position: Position | None
    fills: list[Fill]


class BrokerQueryService:
    """Coordinates read-only broker-order retrieval."""

    def __init__(
        self,
        broker_order_repository: BrokerOrderRepository,
        order_intent_repository: OrderIntentRepository,
        position_repository: PositionRepository,
        fill_repository: FillRepository,
    ) -> None:
        self._broker_orders = broker_order_repository
        self._order_intents = order_intent_repository
        self._positions = position_repository
        self._fills = fill_repository

    def list_broker_orders(
        self,
        *,
        provider: str | None = None,
        status: BrokerOrderStatus | None = None,
        position_id: UUID | None = None,
        order_intent_id: UUID | None = None,
        sort: Literal["oldest", "newest"] = "oldest",
    ) -> list[BrokerOrder]:
        """Return broker orders with exact filters and chronological sorting."""
        broker_orders = self._broker_orders.list_all()
        if provider is not None:
            broker_orders = [
                broker_order
                for broker_order in broker_orders
                if broker_order.provider == provider
            ]
        if status is not None:
            broker_orders = [
                broker_order
                for broker_order in broker_orders
                if broker_order.status == status
            ]
        if position_id is not None:
            broker_orders = [
                broker_order
                for broker_order in broker_orders
                if broker_order.position_id == position_id
            ]
        if order_intent_id is not None:
            broker_orders = [
                broker_order
                for broker_order in broker_orders
                if broker_order.order_intent_id == order_intent_id
            ]
        return sorted(
            broker_orders,
            key=lambda broker_order: broker_order.submitted_at,
            reverse=sort == "newest",
        )

    def get_broker_order_detail(self, broker_order_id: UUID) -> BrokerOrderDetail:
        """Return one broker order with linked local records when present."""
        broker_order = self._broker_orders.get(broker_order_id)
        if broker_order is None:
            raise ValueError("Broker order does not exist.")
        fills = sorted(
            self._fills.list_by_broker_order_id(broker_order.id),
            key=lambda fill: fill.filled_at,
        )
        return BrokerOrderDetail(
            broker_order=broker_order,
            order_intent=self._order_intents.get(broker_order.order_intent_id),
            position=self._positions.get(broker_order.position_id),
            fills=fills,
        )
