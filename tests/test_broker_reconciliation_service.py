"""Tests for explicit broker reconciliation and batch sync workflows."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from trading_system.domain.trading.broker_order import BrokerOrder, BrokerOrderStatus
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.order_intent import OrderIntent, OrderSide, OrderType
from trading_system.domain.trading.position import Position
from trading_system.infrastructure.memory.repositories import (
    InMemoryBrokerOrderRepository,
    InMemoryFillRepository,
    InMemoryLifecycleEventRepository,
    InMemoryOrderIntentRepository,
    InMemoryPositionRepository,
)
from trading_system.ports.broker import (
    BrokerOrderSnapshot,
    BrokerOrderSync,
    BrokerSubmission,
)
from trading_system.services.broker_reconciliation_service import (
    BrokerReconciliationService,
)


def test_batch_sync_imports_one_fill_and_stays_idempotent() -> None:
    """Batch sync imports exactly one local fill for a filled remote order."""
    workflow = _workflow(
        snapshots=[],
        syncs={
            "alpaca-order-1": BrokerOrderSync(
                status=BrokerOrderStatus.FILLED,
                updated_at=_now(),
                fill_price=Decimal("25.75"),
            )
        },
    )
    broker_order = workflow.add_local_broker_order("alpaca-order-1")

    first = workflow.service.sync_submitted_orders("alpaca")
    second = workflow.service.sync_submitted_orders("alpaca")

    assert len(first) == 1
    assert first[0].broker_order.status == BrokerOrderStatus.FILLED
    assert first[0].fill is not None
    assert second == []
    assert workflow.fills.list_by_broker_order_id(broker_order.id) == [first[0].fill]


def test_batch_sync_updates_submitted_canceled_and_rejected_statuses() -> None:
    """Remote non-fill statuses update submitted local broker orders."""
    workflow = _workflow(
        snapshots=[],
        syncs={
            "alpaca-order-1": BrokerOrderSync(
                status=BrokerOrderStatus.CANCELED,
                updated_at=_now(),
            ),
            "alpaca-order-2": BrokerOrderSync(
                status=BrokerOrderStatus.REJECTED,
                updated_at=_now(),
            ),
            "alpaca-order-3": BrokerOrderSync(
                status=BrokerOrderStatus.SUBMITTED,
                updated_at=_now(),
            ),
        },
    )
    canceled = workflow.add_local_broker_order("alpaca-order-1")
    rejected = workflow.add_local_broker_order("alpaca-order-2")
    submitted = workflow.add_local_broker_order("alpaca-order-3")

    workflow.service.sync_submitted_orders("alpaca")

    assert workflow.broker_orders.get(canceled.id).status == BrokerOrderStatus.CANCELED
    assert workflow.broker_orders.get(rejected.id).status == BrokerOrderStatus.REJECTED
    assert workflow.broker_orders.get(submitted.id).status == BrokerOrderStatus.SUBMITTED
    events = workflow.lifecycle_events.list_by_entity("BrokerOrder", canceled.id)
    assert [event.event_type for event in events] == ["BROKER_ORDER_SYNCED"]


def test_reconcile_reports_terminal_status_and_fill_mismatches() -> None:
    """Terminal local records are not redefined by contradictory broker facts."""
    workflow = _workflow(snapshots=[], syncs={})
    filled = workflow.add_local_broker_order(
        "alpaca-order-1",
        status=BrokerOrderStatus.FILLED,
    )
    workflow.add_fill(filled, price=Decimal("25.75"))
    rejected = workflow.add_local_broker_order(
        "alpaca-order-2",
        status=BrokerOrderStatus.REJECTED,
    )
    workflow.client.snapshots = [
        _snapshot("alpaca-order-1", BrokerOrderStatus.FILLED, fill_price=Decimal("26")),
        _snapshot("alpaca-order-2", BrokerOrderStatus.SUBMITTED),
    ]

    report = workflow.service.reconcile_orders("alpaca")

    assert len(report.fill_mismatch) == 1
    assert len(report.status_mismatch) == 1
    assert workflow.broker_orders.get(filled.id).status == BrokerOrderStatus.FILLED
    assert workflow.broker_orders.get(rejected.id).status == BrokerOrderStatus.REJECTED
    assert [
        event.event_type
        for event in workflow.lifecycle_events.list_by_entity("BrokerOrder", filled.id)
    ] == ["BROKER_ORDER_RECONCILIATION_MISMATCH"]


def test_reconcile_surfaces_missing_remote_and_broker_only_without_import() -> None:
    """Broker-only records are report-only and missing remotes are visible."""
    workflow = _workflow(
        snapshots=[
            _snapshot("broker-only-order", BrokerOrderStatus.SUBMITTED),
        ],
        syncs={},
    )
    local = workflow.add_local_broker_order(
        "missing-remote-order",
        status=BrokerOrderStatus.CANCELED,
    )

    report = workflow.service.reconcile_orders("alpaca")

    assert report.missing_remote == [local]
    assert [snapshot.provider_order_id for snapshot in report.broker_only] == [
        "broker-only-order"
    ]
    assert len(workflow.broker_orders.list_all()) == 1
    events = workflow.lifecycle_events.list_by_entity("BrokerOrder", local.id)
    assert events[0].details["mismatch_type"] == "missing_remote"


def test_reconcile_updates_submitted_remote_fill_through_existing_import_path() -> None:
    """Reconciliation uses the same idempotent fill import path as order sync."""
    workflow = _workflow(
        snapshots=[
            _snapshot("alpaca-order-1", BrokerOrderStatus.FILLED, fill_price=Decimal("25.75")),
        ],
        syncs={
            "alpaca-order-1": BrokerOrderSync(
                status=BrokerOrderStatus.FILLED,
                updated_at=_now(),
                fill_price=Decimal("25.75"),
            )
        },
    )
    broker_order = workflow.add_local_broker_order("alpaca-order-1")

    report = workflow.service.reconcile_orders("alpaca")

    assert len(report.updated) == 1
    assert report.updated[0].fill is not None
    assert workflow.broker_orders.get(broker_order.id).status == BrokerOrderStatus.FILLED


class _Workflow:
    def __init__(self, client: "_FakeBrokerClient") -> None:
        self.order_intents = InMemoryOrderIntentRepository()
        self.positions = InMemoryPositionRepository()
        self.broker_orders = InMemoryBrokerOrderRepository()
        self.fills = InMemoryFillRepository()
        self.lifecycle_events = InMemoryLifecycleEventRepository()
        self.client = client
        self.service = BrokerReconciliationService(
            order_intent_repository=self.order_intents,
            position_repository=self.positions,
            broker_order_repository=self.broker_orders,
            fill_repository=self.fills,
            lifecycle_event_repository=self.lifecycle_events,
            broker_client=client,
        )

    def add_local_broker_order(
        self,
        provider_order_id: str,
        *,
        status: BrokerOrderStatus = BrokerOrderStatus.SUBMITTED,
    ) -> BrokerOrder:
        order_intent = OrderIntent(
            trade_plan_id=uuid4(),
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("100"),
            limit_price=Decimal("25.50"),
        )
        position = Position(
            trade_plan_id=order_intent.trade_plan_id,
            instrument_id=uuid4(),
            purpose="swing",
            opened_at=_now(),
        )
        broker_order = BrokerOrder(
            order_intent_id=order_intent.id,
            position_id=position.id,
            provider="alpaca",
            provider_order_id=provider_order_id,
            symbol=order_intent.symbol,
            side=order_intent.side,
            order_type=order_intent.order_type,
            quantity=order_intent.quantity,
            limit_price=order_intent.limit_price,
            status=status,
            submitted_at=_now(),
            updated_at=_now(),
        )
        self.order_intents.add(order_intent)
        self.positions.add(position)
        self.broker_orders.add(broker_order)
        return broker_order

    def add_fill(self, broker_order: BrokerOrder, *, price: Decimal) -> Fill:
        fill = Fill(
            position_id=broker_order.position_id,
            side=broker_order.side.value,
            quantity=broker_order.quantity,
            price=price,
            order_intent_id=broker_order.order_intent_id,
            broker_order_id=broker_order.id,
            source="broker:alpaca",
        )
        self.fills.add(fill)
        return fill


class _FakeBrokerClient:
    provider = "alpaca"

    def __init__(self, *, snapshots, syncs) -> None:
        self.snapshots = snapshots
        self.syncs = syncs

    def submit_order(self, order_intent, position):
        return BrokerSubmission(
            provider=self.provider,
            provider_order_id="unused",
            status=BrokerOrderStatus.SUBMITTED,
            submitted_at=_now(),
            updated_at=_now(),
        )

    def sync_order(self, broker_order_id, simulated_fill_price=None):
        assert simulated_fill_price is None
        return self.syncs[broker_order_id]

    def list_order_snapshots(self):
        return self.snapshots


def _workflow(*, snapshots, syncs) -> _Workflow:
    return _Workflow(_FakeBrokerClient(snapshots=snapshots, syncs=syncs))


def _snapshot(
    provider_order_id: str,
    status: BrokerOrderStatus,
    *,
    fill_price: Decimal | None = None,
) -> BrokerOrderSnapshot:
    return BrokerOrderSnapshot(
        provider="alpaca",
        provider_order_id=provider_order_id,
        status=status,
        updated_at=_now(),
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=Decimal("100"),
        fill_price=fill_price,
    )


def _now() -> datetime:
    return datetime(2026, 5, 3, tzinfo=UTC)
