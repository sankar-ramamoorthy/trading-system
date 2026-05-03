"""Broker adapter implementations for local paper execution workflows."""

from datetime import UTC, datetime
from decimal import Decimal

from trading_system.domain.trading.broker_order import BrokerOrderStatus
from trading_system.domain.trading.order_intent import OrderIntent
from trading_system.domain.trading.position import Position
from trading_system.ports.broker import BrokerClient, BrokerOrderSync, BrokerSubmission


class SimulatedPaperBrokerClient(BrokerClient):
    """Deterministic paper broker adapter with no external network calls."""

    provider = "simulated"

    def submit_order(
        self,
        order_intent: OrderIntent,
        position: Position,
    ) -> BrokerSubmission:
        """Return a deterministic submitted order response."""
        timestamp = datetime.now(UTC)
        return BrokerSubmission(
            provider=self.provider,
            provider_order_id=f"sim-{order_intent.id}",
            status=BrokerOrderStatus.SUBMITTED,
            submitted_at=timestamp,
            updated_at=timestamp,
        )

    def sync_order(
        self,
        broker_order_id: str,
        simulated_fill_price: Decimal | None = None,
    ) -> BrokerOrderSync:
        """Fill an order only when an explicit simulated fill price is supplied."""
        if simulated_fill_price is None:
            raise ValueError("Simulated fill price is required to sync a paper order.")
        if simulated_fill_price <= 0:
            raise ValueError("Simulated fill price must be positive.")
        return BrokerOrderSync(
            status=BrokerOrderStatus.FILLED,
            updated_at=datetime.now(UTC),
            fill_price=simulated_fill_price,
        )
