"""Order intent entity representing the system's planned execution instruction."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class OrderSide(StrEnum):
    """Supported order directions for the initial manual execution slice."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Supported order types for system-originated intent records."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderIntentStatus(StrEnum):
    """Minimal lifecycle states for persisted execution intent."""

    CREATED = "created"


@dataclass(frozen=True)
class OrderIntent:
    """A system-generated intent to execute part of an approved trade plan."""

    trade_plan_id: UUID
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    status: OrderIntentStatus = OrderIntentStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    notes: str | None = None
    id: UUID = field(default_factory=uuid4)
