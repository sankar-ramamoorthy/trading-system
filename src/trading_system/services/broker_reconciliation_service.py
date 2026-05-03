"""Explicit broker reconciliation workflows for local broker orders."""

from dataclasses import dataclass
from decimal import Decimal

from trading_system.domain.trading.broker_order import BrokerOrder, BrokerOrderStatus
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.ports.broker import BrokerClient, BrokerOrderSnapshot
from trading_system.ports.repositories import (
    BrokerOrderRepository,
    FillRepository,
    LifecycleEventRepository,
    OrderIntentRepository,
    PositionRepository,
)
from trading_system.services.broker_execution_service import BrokerExecutionService


@dataclass(frozen=True)
class BrokerOrderSyncItem:
    """Result for one local broker order touched by batch sync."""

    broker_order: BrokerOrder
    previous_status: BrokerOrderStatus
    fill: Fill | None

    @property
    def changed(self) -> bool:
        """Return whether sync imported a fill or changed local status."""
        return self.fill is not None or self.previous_status != self.broker_order.status


@dataclass(frozen=True)
class BrokerReconciliationReport:
    """Summary of local-vs-provider broker order reconciliation."""

    matched: list[BrokerOrder]
    updated: list[BrokerOrderSyncItem]
    missing_remote: list[BrokerOrder]
    broker_only: list[BrokerOrderSnapshot]
    status_mismatch: list[tuple[BrokerOrder, BrokerOrderSnapshot]]
    fill_mismatch: list[tuple[BrokerOrder, BrokerOrderSnapshot, Fill | None]]


class BrokerReconciliationService:
    """Compares local broker-order audit records to provider execution facts."""

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
        self._broker_orders = broker_order_repository
        self._fills = fill_repository
        self._lifecycle_events = lifecycle_event_repository
        self._broker_client = broker_client
        self._execution = BrokerExecutionService(
            order_intent_repository=order_intent_repository,
            position_repository=position_repository,
            broker_order_repository=broker_order_repository,
            fill_repository=fill_repository,
            lifecycle_event_repository=lifecycle_event_repository,
            broker_client=broker_client,
        )

    def sync_submitted_orders(self, provider: str) -> list[BrokerOrderSyncItem]:
        """Sync every local submitted broker order for one provider."""
        self._require_provider(provider)
        results: list[BrokerOrderSyncItem] = []
        for broker_order in self._local_orders(provider):
            if broker_order.status != BrokerOrderStatus.SUBMITTED:
                continue
            synced = self._execution.sync_paper_order(broker_order.id)
            results.append(
                BrokerOrderSyncItem(
                    broker_order=synced.broker_order,
                    previous_status=broker_order.status,
                    fill=synced.fill,
                )
            )
        return results

    def reconcile_orders(self, provider: str) -> BrokerReconciliationReport:
        """Compare local broker orders to provider snapshots."""
        self._require_provider(provider)
        remote_by_provider_id = {
            snapshot.provider_order_id: snapshot
            for snapshot in self._broker_client.list_order_snapshots()
        }
        local_orders = self._local_orders(provider)
        local_by_provider_id = {
            broker_order.provider_order_id: broker_order
            for broker_order in local_orders
        }

        matched: list[BrokerOrder] = []
        updated: list[BrokerOrderSyncItem] = []
        missing_remote: list[BrokerOrder] = []
        status_mismatch: list[tuple[BrokerOrder, BrokerOrderSnapshot]] = []
        fill_mismatch: list[tuple[BrokerOrder, BrokerOrderSnapshot, Fill | None]] = []

        for broker_order in local_orders:
            snapshot = remote_by_provider_id.get(broker_order.provider_order_id)
            if snapshot is None:
                missing_remote.append(broker_order)
                self._record_mismatch(
                    broker_order,
                    mismatch_type="missing_remote",
                    remote_status=None,
                )
                continue

            if broker_order.status == BrokerOrderStatus.SUBMITTED:
                synced = self._execution.sync_paper_order(broker_order.id)
                item = BrokerOrderSyncItem(
                    broker_order=synced.broker_order,
                    previous_status=broker_order.status,
                    fill=synced.fill,
                )
                if item.changed:
                    updated.append(item)
                else:
                    matched.append(item.broker_order)
                continue

            if broker_order.status != snapshot.status:
                status_mismatch.append((broker_order, snapshot))
                self._record_mismatch(
                    broker_order,
                    mismatch_type="status_mismatch",
                    remote_status=snapshot.status,
                )
                continue

            if broker_order.status == BrokerOrderStatus.FILLED:
                local_fill = self._first_fill(broker_order)
                if not _fill_prices_match(local_fill, snapshot.fill_price):
                    fill_mismatch.append((broker_order, snapshot, local_fill))
                    self._record_mismatch(
                        broker_order,
                        mismatch_type="fill_mismatch",
                        remote_status=snapshot.status,
                    )
                    continue

            matched.append(broker_order)

        broker_only = [
            snapshot
            for snapshot in remote_by_provider_id.values()
            if snapshot.provider_order_id not in local_by_provider_id
        ]

        return BrokerReconciliationReport(
            matched=matched,
            updated=updated,
            missing_remote=missing_remote,
            broker_only=broker_only,
            status_mismatch=status_mismatch,
            fill_mismatch=fill_mismatch,
        )

    def _require_provider(self, provider: str) -> None:
        if provider != self._broker_client.provider:
            raise ValueError(f"Unsupported paper broker provider: {provider}.")

    def _local_orders(self, provider: str) -> list[BrokerOrder]:
        return [
            broker_order
            for broker_order in self._broker_orders.list_all()
            if broker_order.provider == provider
        ]

    def _first_fill(self, broker_order: BrokerOrder) -> Fill | None:
        fills = sorted(
            self._fills.list_by_broker_order_id(broker_order.id),
            key=lambda fill: fill.filled_at,
        )
        return fills[0] if fills else None

    def _record_mismatch(
        self,
        broker_order: BrokerOrder,
        *,
        mismatch_type: str,
        remote_status: BrokerOrderStatus | None,
    ) -> None:
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=broker_order.id,
                entity_type="BrokerOrder",
                event_type="BROKER_ORDER_RECONCILIATION_MISMATCH",
                note=f"Broker reconciliation mismatch for order {broker_order.id}.",
                details={
                    "broker_order_id": str(broker_order.id),
                    "provider": broker_order.provider,
                    "provider_order_id": broker_order.provider_order_id,
                    "mismatch_type": mismatch_type,
                    "local_status": broker_order.status.value,
                    "remote_status": None
                    if remote_status is None
                    else remote_status.value,
                },
            )
        )


def _fill_prices_match(fill: Fill | None, remote_price: Decimal | None) -> bool:
    if fill is None:
        return remote_price is None
    return remote_price is not None and fill.price == remote_price
