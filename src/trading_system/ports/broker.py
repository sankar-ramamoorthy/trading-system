"""Broker execution port definitions."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from trading_system.domain.trading.broker_order import BrokerOrderStatus
from trading_system.domain.trading.order_intent import OrderIntent
from trading_system.domain.trading.position import Position


@dataclass(frozen=True)
class BrokerSubmission:
    """Provider response for a submitted broker order."""

    provider: str
    provider_order_id: str
    status: BrokerOrderStatus
    submitted_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class BrokerOrderSync:
    """Provider response when syncing a submitted broker order."""

    status: BrokerOrderStatus
    updated_at: datetime
    fill_price: Decimal | None = None


class BrokerClient(Protocol):
    """Provider-agnostic broker execution client boundary."""

    provider: str

    def submit_order(
        self,
        order_intent: OrderIntent,
        position: Position,
    ) -> BrokerSubmission:
        """Submit an order intent to the broker boundary."""
        ...

    def sync_order(
        self,
        broker_order_id: str,
        simulated_fill_price: Decimal | None = None,
    ) -> BrokerOrderSync:
        """Return provider-side status for a previously submitted order."""
        ...
