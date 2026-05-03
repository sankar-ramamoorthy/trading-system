"""JSON-backed repository implementations for local durable workflows."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from json import JSONDecodeError
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
from typing import Any
from uuid import UUID

from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.rules.violation import Violation
from trading_system.domain.trading.broker_order import BrokerOrder, BrokerOrderStatus
from trading_system.domain.trading.fill import Fill
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.order_intent import (
    OrderIntent,
    OrderIntentStatus,
    OrderSide,
    OrderType,
)
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.position import Position
from trading_system.domain.trading.review import TradeReview
from trading_system.domain.trading.thesis import TradeThesis


COLLECTIONS = (
    "trade_ideas",
    "trade_theses",
    "trade_plans",
    "positions",
    "order_intents",
    "broker_orders",
    "fills",
    "trade_reviews",
    "market_context_snapshots",
    "lifecycle_events",
    "rule_evaluations",
    "violations",
)


class JsonPersistenceError(RuntimeError):
    """Raised when the local JSON store cannot be read safely."""


@dataclass(frozen=True)
class JsonStoreValidation:
    """Summary of a validated local JSON store."""

    store_path: Path
    collection_counts: dict[str, int]

    @property
    def total_record_count(self) -> int:
        """Return the total number of stored records across all collections."""
        return sum(self.collection_counts.values())


class JsonStore:
    """Small JSON document store with atomic replacement writes."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def read(self) -> dict[str, dict[str, Any]]:
        """Read the store, creating an empty document when it does not exist."""
        if not self.path.exists():
            return _empty_store()

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except JSONDecodeError as exc:
            raise JsonPersistenceError(
                f"JSON persistence store is invalid: {self.path}"
            ) from exc

        if not isinstance(raw, dict):
            raise JsonPersistenceError(
                f"JSON persistence store root must be an object: {self.path}"
            )

        data = _empty_store()
        for collection in COLLECTIONS:
            value = raw.get(collection, {})
            if not isinstance(value, dict):
                raise JsonPersistenceError(
                    f"JSON persistence collection must be an object: {collection}"
                )
            data[collection] = value
        return data

    def write(self, data: dict[str, dict[str, Any]]) -> None:
        """Persist the full store using a same-directory temporary file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
        ) as tmp:
            json.dump(data, tmp, indent=2, sort_keys=True)
            tmp.write("\n")
            temp_path = Path(tmp.name)
        temp_path.replace(self.path)

    def upsert(self, collection: str, item_id: UUID, record: dict[str, Any]) -> None:
        """Insert or replace one record in a collection."""
        data = self.read()
        data[collection][str(item_id)] = record
        self.write(data)

    def get(self, collection: str, item_id: UUID) -> dict[str, Any] | None:
        """Return a raw record by UUID."""
        return self.read()[collection].get(str(item_id))


def validate_json_store(path: Path | str) -> JsonStoreValidation:
    """Validate an existing JSON store and return collection record counts."""
    store_path = Path(path)
    if not store_path.exists():
        raise JsonPersistenceError(f"JSON persistence store does not exist: {store_path}")

    data = JsonStore(store_path).read()
    return JsonStoreValidation(
        store_path=store_path,
        collection_counts={
            collection: len(data[collection]) for collection in COLLECTIONS
        },
    )


def backup_json_store(
    store_path: Path | str,
    output_dir: Path | str,
    *,
    timestamp: datetime | None = None,
) -> Path:
    """Create an exact timestamped JSON backup of an existing valid store."""
    source_path = Path(store_path)
    validate_json_store(source_path)

    backup_dir = Path(output_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_timestamp = timestamp or datetime.now().astimezone()
    backup_path = backup_dir / (
        "trading-system-store-"
        f"{backup_timestamp.strftime('%Y%m%d-%H%M%S')}.json"
    )
    shutil.copyfile(source_path, backup_path)
    return backup_path


def restore_json_store(
    backup_path: Path | str,
    store_path: Path | str,
    *,
    overwrite: bool,
) -> None:
    """Restore a validated backup into the configured JSON store path."""
    source_path = Path(backup_path)
    target_path = Path(store_path)
    validate_json_store(source_path)
    data = JsonStore(source_path).read()
    if target_path.exists() and not overwrite:
        raise JsonPersistenceError(
            "JSON persistence store already exists. Use --overwrite to replace it."
        )
    JsonStore(target_path).write(data)


class JsonTradeIdeaRepository:
    """Stores trade ideas in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, idea: TradeIdea) -> None:
        """Persist a trade idea."""
        self._store.upsert("trade_ideas", idea.id, _trade_idea_to_record(idea))

    def get(self, idea_id: UUID) -> TradeIdea | None:
        """Return a trade idea by identity."""
        record = self._store.get("trade_ideas", idea_id)
        return None if record is None else _trade_idea_from_record(record)

    def list_all(self) -> list[TradeIdea]:
        """Return all trade ideas."""
        return [
            _trade_idea_from_record(record)
            for record in self._store.read()["trade_ideas"].values()
        ]


class JsonTradeThesisRepository:
    """Stores trade theses in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, thesis: TradeThesis) -> None:
        """Persist a trade thesis."""
        self._store.upsert("trade_theses", thesis.id, _trade_thesis_to_record(thesis))

    def get(self, thesis_id: UUID) -> TradeThesis | None:
        """Return a trade thesis by identity."""
        record = self._store.get("trade_theses", thesis_id)
        return None if record is None else _trade_thesis_from_record(record)

    def list_all(self) -> list[TradeThesis]:
        """Return all trade theses."""
        return [
            _trade_thesis_from_record(record)
            for record in self._store.read()["trade_theses"].values()
        ]


class JsonTradePlanRepository:
    """Stores trade plans in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, plan: TradePlan) -> None:
        """Persist a trade plan."""
        self._store.upsert("trade_plans", plan.id, _trade_plan_to_record(plan))

    def get(self, plan_id: UUID) -> TradePlan | None:
        """Return a trade plan by identity."""
        record = self._store.get("trade_plans", plan_id)
        return None if record is None else _trade_plan_from_record(record)

    def update(self, plan: TradePlan) -> None:
        """Persist changes to a trade plan."""
        self.add(plan)

    def list_all(self) -> list[TradePlan]:
        """Return all trade plans."""
        return [
            _trade_plan_from_record(record)
            for record in self._store.read()["trade_plans"].values()
        ]


class JsonPositionRepository:
    """Stores positions in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, position: Position) -> None:
        """Persist a position."""
        self._store.upsert("positions", position.id, _position_to_record(position))

    def get(self, position_id: UUID) -> Position | None:
        """Return a position by identity."""
        record = self._store.get("positions", position_id)
        return None if record is None else _position_from_record(record)

    def update(self, position: Position) -> None:
        """Persist changes to a position."""
        self.add(position)

    def list_all(self) -> list[Position]:
        """Return all positions."""
        return [
            _position_from_record(record)
            for record in self._store.read()["positions"].values()
        ]


class JsonFillRepository:
    """Stores manual fills in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, fill: Fill) -> None:
        """Persist a manual fill."""
        self._store.upsert("fills", fill.id, _fill_to_record(fill))

    def get(self, fill_id: UUID) -> Fill | None:
        """Return a fill by identity."""
        record = self._store.get("fills", fill_id)
        return None if record is None else _fill_from_record(record)

    def list_by_position_id(self, position_id: UUID) -> list[Fill]:
        """Return fills for a position."""
        return [
            fill
            for fill in (
                _fill_from_record(record)
                for record in self._store.read()["fills"].values()
            )
            if fill.position_id == position_id
        ]

    def list_by_broker_order_id(self, broker_order_id: UUID) -> list[Fill]:
        """Return fills linked to a broker order."""
        return [
            fill
            for fill in (
                _fill_from_record(record)
                for record in self._store.read()["fills"].values()
            )
            if fill.broker_order_id == broker_order_id
        ]


class JsonOrderIntentRepository:
    """Stores order intents in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, order_intent: OrderIntent) -> None:
        """Persist an order intent."""
        self._store.upsert(
            "order_intents",
            order_intent.id,
            _order_intent_to_record(order_intent),
        )

    def get(self, order_intent_id: UUID) -> OrderIntent | None:
        """Return an order intent by identity."""
        record = self._store.get("order_intents", order_intent_id)
        return None if record is None else _order_intent_from_record(record)

    def update(self, order_intent: OrderIntent) -> None:
        """Persist changes to an order intent."""
        self.add(order_intent)

    def list_by_trade_plan_id(self, trade_plan_id: UUID) -> list[OrderIntent]:
        """Return order intents linked to a trade plan."""
        return [
            order_intent
            for order_intent in (
                _order_intent_from_record(record)
                for record in self._store.read()["order_intents"].values()
            )
            if order_intent.trade_plan_id == trade_plan_id
        ]


class JsonBrokerOrderRepository:
    """Stores broker orders in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, broker_order: BrokerOrder) -> None:
        """Persist a broker order."""
        self._store.upsert(
            "broker_orders",
            broker_order.id,
            _broker_order_to_record(broker_order),
        )

    def get(self, broker_order_id: UUID) -> BrokerOrder | None:
        """Return a broker order by identity."""
        record = self._store.get("broker_orders", broker_order_id)
        return None if record is None else _broker_order_from_record(record)

    def update(self, broker_order: BrokerOrder) -> None:
        """Persist changes to a broker order."""
        self.add(broker_order)

    def get_by_order_intent_id(self, order_intent_id: UUID) -> BrokerOrder | None:
        """Return the broker order for one order intent, if present."""
        for record in self._store.read()["broker_orders"].values():
            broker_order = _broker_order_from_record(record)
            if broker_order.order_intent_id == order_intent_id:
                return broker_order
        return None

    def list_all(self) -> list[BrokerOrder]:
        """Return all broker orders."""
        return [
            _broker_order_from_record(record)
            for record in self._store.read()["broker_orders"].values()
        ]


class JsonLifecycleEventRepository:
    """Stores lifecycle events in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, event: LifecycleEvent) -> None:
        """Persist a lifecycle event."""
        self._store.upsert(
            "lifecycle_events",
            event.id,
            _lifecycle_event_to_record(event),
        )

    def get(self, event_id: UUID) -> LifecycleEvent | None:
        """Return a lifecycle event by identity."""
        record = self._store.get("lifecycle_events", event_id)
        return None if record is None else _lifecycle_event_from_record(record)

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[LifecycleEvent]:
        """Return lifecycle events for an entity."""
        return sorted(
            [
                event
                for event in (
                    _lifecycle_event_from_record(record)
                    for record in self._store.read()["lifecycle_events"].values()
                )
                if event.entity_type == entity_type and event.entity_id == entity_id
            ],
            key=lambda event: event.occurred_at,
        )


class JsonTradeReviewRepository:
    """Stores trade reviews in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, review: TradeReview) -> None:
        """Persist a trade review."""
        self._store.upsert("trade_reviews", review.id, _trade_review_to_record(review))

    def get(self, review_id: UUID) -> TradeReview | None:
        """Return a trade review by identity."""
        record = self._store.get("trade_reviews", review_id)
        return None if record is None else _trade_review_from_record(record)

    def get_by_position_id(self, position_id: UUID) -> TradeReview | None:
        """Return the review for a position, if one exists."""
        for record in self._store.read()["trade_reviews"].values():
            review = _trade_review_from_record(record)
            if review.position_id == position_id:
                return review
        return None

    def list_all(self) -> list[TradeReview]:
        """Return all trade reviews."""
        return [
            _trade_review_from_record(record)
            for record in self._store.read()["trade_reviews"].values()
        ]


class JsonMarketContextSnapshotRepository:
    """Stores read-only market context snapshots in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, snapshot: MarketContextSnapshot) -> None:
        """Persist a market context snapshot."""
        self._store.upsert(
            "market_context_snapshots",
            snapshot.id,
            _market_context_snapshot_to_record(snapshot),
        )

    def get(self, snapshot_id: UUID) -> MarketContextSnapshot | None:
        """Return a market context snapshot by identity."""
        record = self._store.get("market_context_snapshots", snapshot_id)
        return None if record is None else _market_context_snapshot_from_record(record)

    def list_all(self) -> list[MarketContextSnapshot]:
        """Return all market context snapshots."""
        return sorted(
            [
                _market_context_snapshot_from_record(record)
                for record in self._store.read()["market_context_snapshots"].values()
            ],
            key=lambda snapshot: snapshot.captured_at,
        )

    def list_by_instrument_id(self, instrument_id: UUID) -> list[MarketContextSnapshot]:
        """Return snapshots for one instrument."""
        return sorted(
            [
                snapshot
                for snapshot in (
                    _market_context_snapshot_from_record(record)
                    for record in self._store.read()["market_context_snapshots"].values()
                )
                if snapshot.instrument_id == instrument_id
            ],
            key=lambda snapshot: snapshot.captured_at,
        )

    def list_by_target(
        self,
        target_type: str,
        target_id: UUID,
    ) -> list[MarketContextSnapshot]:
        """Return snapshots linked to one planning or review target."""
        return sorted(
            [
                snapshot
                for snapshot in (
                    _market_context_snapshot_from_record(record)
                    for record in self._store.read()["market_context_snapshots"].values()
                )
                if snapshot.target_type == target_type and snapshot.target_id == target_id
            ],
            key=lambda snapshot: snapshot.captured_at,
        )


class JsonRuleEvaluationRepository:
    """Stores rule evaluation artifacts in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, evaluation: RuleEvaluation) -> None:
        """Persist a rule evaluation."""
        self._store.upsert(
            "rule_evaluations",
            evaluation.id,
            _rule_evaluation_to_record(evaluation),
        )

    def get(self, evaluation_id: UUID) -> RuleEvaluation | None:
        """Return a rule evaluation by identity."""
        record = self._store.get("rule_evaluations", evaluation_id)
        return None if record is None else _rule_evaluation_from_record(record)

    def list_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[RuleEvaluation]:
        """Return persisted evaluations for one domain entity."""
        return [
            evaluation
            for evaluation in (
                _rule_evaluation_from_record(record)
                for record in self._store.read()["rule_evaluations"].values()
            )
            if evaluation.entity_type == entity_type and evaluation.entity_id == entity_id
        ]


class JsonViolationRepository:
    """Stores rule violations in a local JSON document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def add(self, violation: Violation) -> None:
        """Persist a rule violation."""
        self._store.upsert("violations", violation.id, _violation_to_record(violation))

    def get(self, violation_id: UUID) -> Violation | None:
        """Return a rule violation by identity."""
        record = self._store.get("violations", violation_id)
        return None if record is None else _violation_from_record(record)


@dataclass(frozen=True)
class JsonRepositorySet:
    """Concrete JSON repositories used to wire CLI workflows."""

    store_path: Path
    ideas: JsonTradeIdeaRepository
    theses: JsonTradeThesisRepository
    plans: JsonTradePlanRepository
    positions: JsonPositionRepository
    order_intents: JsonOrderIntentRepository
    broker_orders: JsonBrokerOrderRepository
    fills: JsonFillRepository
    lifecycle_events: JsonLifecycleEventRepository
    reviews: JsonTradeReviewRepository
    market_context_snapshots: JsonMarketContextSnapshotRepository
    evaluations: JsonRuleEvaluationRepository
    violations: JsonViolationRepository


def build_json_repositories(path: Path | str) -> JsonRepositorySet:
    """Build all JSON-backed repositories over one shared store."""
    store_path = Path(path)
    store = JsonStore(store_path)
    return JsonRepositorySet(
        store_path=store_path,
        ideas=JsonTradeIdeaRepository(store),
        theses=JsonTradeThesisRepository(store),
        plans=JsonTradePlanRepository(store),
        positions=JsonPositionRepository(store),
        order_intents=JsonOrderIntentRepository(store),
        broker_orders=JsonBrokerOrderRepository(store),
        fills=JsonFillRepository(store),
        lifecycle_events=JsonLifecycleEventRepository(store),
        reviews=JsonTradeReviewRepository(store),
        market_context_snapshots=JsonMarketContextSnapshotRepository(store),
        evaluations=JsonRuleEvaluationRepository(store),
        violations=JsonViolationRepository(store),
    )


def _empty_store() -> dict[str, dict[str, Any]]:
    return {collection: {} for collection in COLLECTIONS}


def _trade_idea_to_record(idea: TradeIdea) -> dict[str, Any]:
    return {
        "id": str(idea.id),
        "instrument_id": str(idea.instrument_id),
        "playbook_id": str(idea.playbook_id),
        "purpose": idea.purpose,
        "direction": idea.direction,
        "horizon": idea.horizon,
        "status": idea.status,
        "created_at": idea.created_at.isoformat(),
    }


def _trade_idea_from_record(record: dict[str, Any]) -> TradeIdea:
    return TradeIdea(
        id=UUID(record["id"]),
        instrument_id=UUID(record["instrument_id"]),
        playbook_id=UUID(record["playbook_id"]),
        purpose=record["purpose"],
        direction=record["direction"],
        horizon=record["horizon"],
        status=record["status"],
        created_at=_datetime(record["created_at"]),
    )


def _trade_thesis_to_record(thesis: TradeThesis) -> dict[str, Any]:
    return {
        "id": str(thesis.id),
        "trade_idea_id": str(thesis.trade_idea_id),
        "reasoning": thesis.reasoning,
        "supporting_evidence": list(thesis.supporting_evidence),
        "risks": list(thesis.risks),
        "disconfirming_signals": list(thesis.disconfirming_signals),
    }


def _trade_thesis_from_record(record: dict[str, Any]) -> TradeThesis:
    return TradeThesis(
        id=UUID(record["id"]),
        trade_idea_id=UUID(record["trade_idea_id"]),
        reasoning=record["reasoning"],
        supporting_evidence=list(record["supporting_evidence"]),
        risks=list(record["risks"]),
        disconfirming_signals=list(record["disconfirming_signals"]),
    )


def _trade_plan_to_record(plan: TradePlan) -> dict[str, Any]:
    return {
        "id": str(plan.id),
        "trade_idea_id": str(plan.trade_idea_id),
        "trade_thesis_id": str(plan.trade_thesis_id),
        "entry_criteria": plan.entry_criteria,
        "invalidation": plan.invalidation,
        "targets": list(plan.targets),
        "risk_model": plan.risk_model,
        "sizing_assumptions": plan.sizing_assumptions,
        "approval_state": plan.approval_state,
        "created_at": plan.created_at.isoformat(),
    }


def _trade_plan_from_record(record: dict[str, Any]) -> TradePlan:
    return TradePlan(
        id=UUID(record["id"]),
        trade_idea_id=UUID(record["trade_idea_id"]),
        trade_thesis_id=UUID(record["trade_thesis_id"]),
        entry_criteria=record["entry_criteria"],
        invalidation=record["invalidation"],
        targets=list(record["targets"]),
        risk_model=record["risk_model"],
        sizing_assumptions=record["sizing_assumptions"],
        approval_state=record["approval_state"],
        created_at=_datetime(record["created_at"]),
    )


def _position_to_record(position: Position) -> dict[str, Any]:
    return {
        "id": str(position.id),
        "trade_plan_id": str(position.trade_plan_id),
        "instrument_id": str(position.instrument_id),
        "purpose": position.purpose,
        "lifecycle_state": position.lifecycle_state,
        "opened_at": position.opened_at.isoformat(),
        "closed_at": _optional_datetime_to_string(position.closed_at),
        "total_bought_quantity": str(position.total_bought_quantity),
        "total_sold_quantity": str(position.total_sold_quantity),
        "current_quantity": str(position.current_quantity),
        "average_entry_price": _optional_decimal_to_string(
            position.average_entry_price
        ),
        "closing_fill_id": _optional_uuid_to_string(position.closing_fill_id),
        "close_reason": position.close_reason,
    }


def _position_from_record(record: dict[str, Any]) -> Position:
    return Position(
        id=UUID(record["id"]),
        trade_plan_id=UUID(record["trade_plan_id"]),
        instrument_id=UUID(record["instrument_id"]),
        purpose=record["purpose"],
        lifecycle_state=record["lifecycle_state"],
        opened_at=_datetime(record["opened_at"]),
        closed_at=_optional_datetime(record["closed_at"]),
        total_bought_quantity=Decimal(record["total_bought_quantity"]),
        total_sold_quantity=Decimal(record["total_sold_quantity"]),
        current_quantity=Decimal(record["current_quantity"]),
        average_entry_price=_optional_decimal(record["average_entry_price"]),
        closing_fill_id=_optional_uuid(record["closing_fill_id"]),
        close_reason=record["close_reason"],
    )


def _fill_to_record(fill: Fill) -> dict[str, Any]:
    return {
        "id": str(fill.id),
        "position_id": str(fill.position_id),
        "quantity": str(fill.quantity),
        "price": str(fill.price),
        "side": fill.side,
        "order_intent_id": _optional_uuid_to_string(fill.order_intent_id),
        "broker_order_id": _optional_uuid_to_string(fill.broker_order_id),
        "filled_at": fill.filled_at.isoformat(),
        "notes": fill.notes,
        "source": fill.source,
    }


def _fill_from_record(record: dict[str, Any]) -> Fill:
    return Fill(
        id=UUID(record["id"]),
        position_id=UUID(record["position_id"]),
        quantity=Decimal(record["quantity"]),
        price=Decimal(record["price"]),
        side=record["side"],
        order_intent_id=_optional_uuid(record.get("order_intent_id")),
        broker_order_id=_optional_uuid(record.get("broker_order_id")),
        filled_at=_datetime(record["filled_at"]),
        notes=record.get("notes"),
        source=record.get("source", "manual"),
    )


def _order_intent_to_record(order_intent: OrderIntent) -> dict[str, Any]:
    return {
        "id": str(order_intent.id),
        "trade_plan_id": str(order_intent.trade_plan_id),
        "symbol": order_intent.symbol,
        "side": order_intent.side.value,
        "order_type": order_intent.order_type.value,
        "quantity": str(order_intent.quantity),
        "limit_price": _optional_decimal_to_string(order_intent.limit_price),
        "stop_price": _optional_decimal_to_string(order_intent.stop_price),
        "status": order_intent.status.value,
        "created_at": order_intent.created_at.isoformat(),
        "notes": order_intent.notes,
    }


def _order_intent_from_record(record: dict[str, Any]) -> OrderIntent:
    return OrderIntent(
        id=UUID(record["id"]),
        trade_plan_id=UUID(record["trade_plan_id"]),
        symbol=record["symbol"],
        side=OrderSide(record["side"]),
        order_type=OrderType(record["order_type"]),
        quantity=Decimal(record["quantity"]),
        limit_price=_optional_decimal(record["limit_price"]),
        stop_price=_optional_decimal(record["stop_price"]),
        status=OrderIntentStatus(record["status"]),
        created_at=_datetime(record["created_at"]),
        notes=record["notes"],
    )


def _broker_order_to_record(broker_order: BrokerOrder) -> dict[str, Any]:
    return {
        "id": str(broker_order.id),
        "order_intent_id": str(broker_order.order_intent_id),
        "position_id": str(broker_order.position_id),
        "provider": broker_order.provider,
        "provider_order_id": broker_order.provider_order_id,
        "symbol": broker_order.symbol,
        "side": broker_order.side.value,
        "order_type": broker_order.order_type.value,
        "quantity": str(broker_order.quantity),
        "limit_price": _optional_decimal_to_string(broker_order.limit_price),
        "stop_price": _optional_decimal_to_string(broker_order.stop_price),
        "status": broker_order.status.value,
        "submitted_at": broker_order.submitted_at.isoformat(),
        "updated_at": broker_order.updated_at.isoformat(),
    }


def _broker_order_from_record(record: dict[str, Any]) -> BrokerOrder:
    return BrokerOrder(
        id=UUID(record["id"]),
        order_intent_id=UUID(record["order_intent_id"]),
        position_id=UUID(record["position_id"]),
        provider=record["provider"],
        provider_order_id=record["provider_order_id"],
        symbol=record["symbol"],
        side=OrderSide(record["side"]),
        order_type=OrderType(record["order_type"]),
        quantity=Decimal(record["quantity"]),
        limit_price=_optional_decimal(record["limit_price"]),
        stop_price=_optional_decimal(record["stop_price"]),
        status=BrokerOrderStatus(record["status"]),
        submitted_at=_datetime(record["submitted_at"]),
        updated_at=_datetime(record["updated_at"]),
    )


def _lifecycle_event_to_record(event: LifecycleEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "entity_id": str(event.entity_id),
        "entity_type": event.entity_type,
        "event_type": event.event_type,
        "note": event.note,
        "details": event.details,
        "occurred_at": event.occurred_at.isoformat(),
    }


def _lifecycle_event_from_record(record: dict[str, Any]) -> LifecycleEvent:
    return LifecycleEvent(
        id=UUID(record["id"]),
        entity_id=UUID(record["entity_id"]),
        entity_type=record["entity_type"],
        event_type=record["event_type"],
        note=record["note"],
        details=dict(record["details"]),
        occurred_at=_datetime(record["occurred_at"]),
    )


def _trade_review_to_record(review: TradeReview) -> dict[str, Any]:
    return {
        "id": str(review.id),
        "position_id": str(review.position_id),
        "summary": review.summary,
        "what_went_well": review.what_went_well,
        "what_went_poorly": review.what_went_poorly,
        "lessons_learned": list(review.lessons_learned),
        "follow_up_actions": list(review.follow_up_actions),
        "tags": list(review.tags),
        "rating": review.rating,
        "process_score": review.process_score,
        "setup_quality": review.setup_quality,
        "execution_quality": review.execution_quality,
        "exit_quality": review.exit_quality,
        "reviewed_at": review.reviewed_at.isoformat(),
    }


def _trade_review_from_record(record: dict[str, Any]) -> TradeReview:
    return TradeReview(
        id=UUID(record["id"]),
        position_id=UUID(record["position_id"]),
        summary=record["summary"],
        what_went_well=record["what_went_well"],
        what_went_poorly=record["what_went_poorly"],
        lessons_learned=list(record["lessons_learned"]),
        follow_up_actions=list(record["follow_up_actions"]),
        tags=list(record.get("tags", [])),
        rating=record["rating"],
        process_score=record.get("process_score"),
        setup_quality=record.get("setup_quality"),
        execution_quality=record.get("execution_quality"),
        exit_quality=record.get("exit_quality"),
        reviewed_at=_datetime(record["reviewed_at"]),
    )


def _market_context_snapshot_to_record(
    snapshot: MarketContextSnapshot,
) -> dict[str, Any]:
    return {
        "id": str(snapshot.id),
        "instrument_id": str(snapshot.instrument_id),
        "target_type": snapshot.target_type,
        "target_id": _optional_uuid_to_string(snapshot.target_id),
        "context_type": snapshot.context_type,
        "source": snapshot.source,
        "source_ref": snapshot.source_ref,
        "observed_at": snapshot.observed_at.isoformat(),
        "captured_at": snapshot.captured_at.isoformat(),
        "payload": snapshot.payload,
    }


def _market_context_snapshot_from_record(
    record: dict[str, Any],
) -> MarketContextSnapshot:
    return MarketContextSnapshot(
        id=UUID(record["id"]),
        instrument_id=UUID(record["instrument_id"]),
        target_type=record["target_type"],
        target_id=_optional_uuid(record["target_id"]),
        context_type=record["context_type"],
        source=record["source"],
        source_ref=record["source_ref"],
        observed_at=_datetime(record["observed_at"]),
        captured_at=_datetime(record["captured_at"]),
        payload=dict(record["payload"]),
    )


def _rule_evaluation_to_record(evaluation: RuleEvaluation) -> dict[str, Any]:
    return {
        "id": str(evaluation.id),
        "rule_id": str(evaluation.rule_id),
        "entity_type": evaluation.entity_type,
        "entity_id": str(evaluation.entity_id),
        "passed": evaluation.passed,
        "details": evaluation.details,
        "evaluated_at": evaluation.evaluated_at.isoformat(),
    }


def _rule_evaluation_from_record(record: dict[str, Any]) -> RuleEvaluation:
    return RuleEvaluation(
        id=UUID(record["id"]),
        rule_id=UUID(record["rule_id"]),
        entity_type=record["entity_type"],
        entity_id=UUID(record["entity_id"]),
        passed=record["passed"],
        details=record["details"],
        evaluated_at=_datetime(record["evaluated_at"]),
    )


def _violation_to_record(violation: Violation) -> dict[str, Any]:
    return {
        "id": str(violation.id),
        "rule_id": str(violation.rule_id),
        "message": violation.message,
        "severity": violation.severity,
    }


def _violation_from_record(record: dict[str, Any]) -> Violation:
    return Violation(
        id=UUID(record["id"]),
        rule_id=UUID(record["rule_id"]),
        message=record["message"],
        severity=record["severity"],
    )


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _optional_datetime(value: str | None) -> datetime | None:
    return None if value is None else _datetime(value)


def _optional_datetime_to_string(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _optional_decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _optional_decimal_to_string(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _optional_uuid(value: str | None) -> UUID | None:
    return None if value is None else UUID(value)


def _optional_uuid_to_string(value: UUID | None) -> str | None:
    return None if value is None else str(value)
