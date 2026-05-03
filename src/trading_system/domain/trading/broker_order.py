"""Local broker order record for paper execution boundaries."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from trading_system.domain.trading.order_intent import OrderSide, OrderType


class BrokerOrderStatus(StrEnum):
    """Supported local broker-order lifecycle states."""

    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class BrokerOrder:
    """A local audit record for an order submitted through a broker boundary."""

    order_intent_id: UUID
    position_id: UUID
    provider: str
    provider_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    status: BrokerOrderStatus
    submitted_at: datetime
    updated_at: datetime
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    id: UUID = field(default_factory=uuid4)


def new_submitted_broker_order(
    *,
    order_intent_id: UUID,
    position_id: UUID,
    provider: str,
    provider_order_id: str,
    symbol: str,
    side: OrderSide,
    order_type: OrderType,
    quantity: Decimal,
    limit_price: Decimal | None = None,
    stop_price: Decimal | None = None,
    submitted_at: datetime | None = None,
) -> BrokerOrder:
    """Create a submitted broker-order record with one consistent timestamp."""
    timestamp = submitted_at or datetime.now(UTC)
    return BrokerOrder(
        order_intent_id=order_intent_id,
        position_id=position_id,
        provider=provider,
        provider_order_id=provider_order_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        limit_price=limit_price,
        stop_price=stop_price,
        status=BrokerOrderStatus.SUBMITTED,
        submitted_at=timestamp,
        updated_at=timestamp,
    )
