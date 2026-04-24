"""Service workflow for creating audited order intent records."""

from decimal import Decimal
from uuid import UUID

from trading_system.domain.trading.lifecycle import LifecycleEvent
from trading_system.domain.trading.order_intent import (
    OrderIntent,
    OrderIntentStatus,
    OrderSide,
    OrderType,
)
from trading_system.ports.repositories import (
    LifecycleEventRepository,
    OrderIntentRepository,
    RuleEvaluationRepository,
    TradePlanRepository,
)


class CreateOrderIntentService:
    """Coordinates narrow order-intent creation from an approved trade plan."""

    def __init__(
        self,
        plan_repository: TradePlanRepository,
        order_intent_repository: OrderIntentRepository,
        evaluation_repository: RuleEvaluationRepository,
        lifecycle_event_repository: LifecycleEventRepository,
    ) -> None:
        self._plans = plan_repository
        self._order_intents = order_intent_repository
        self._evaluations = evaluation_repository
        self._lifecycle_events = lifecycle_event_repository

    def create_order_intent(
        self,
        trade_plan_id: UUID,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        limit_price: Decimal | None = None,
        stop_price: Decimal | None = None,
        notes: str | None = None,
    ) -> OrderIntent:
        """Persist a new order intent after approval and rule-gating checks."""
        plan = self._plans.get(trade_plan_id)
        if plan is None:
            raise ValueError("Trade plan does not exist.")
        if plan.approval_state != "approved":
            raise ValueError("Trade plan must be approved before creating an order intent.")

        evaluations = self._evaluations.list_by_entity("TradePlan", plan.id)
        if not evaluations:
            raise ValueError(
                "Trade plan must have persisted passing rule evaluations before creating an order intent."
            )
        if any(not evaluation.passed for evaluation in evaluations):
            raise ValueError(
                "Trade plan has failed rule evaluations and cannot create an order intent."
            )

        order_intent = OrderIntent(
            trade_plan_id=plan.id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            status=OrderIntentStatus.CREATED,
            notes=notes,
        )
        self._order_intents.add(order_intent)
        self._lifecycle_events.add(
            LifecycleEvent(
                entity_id=order_intent.id,
                entity_type="OrderIntent",
                event_type="ORDER_INTENT_CREATED",
                note=f"Created order intent from trade plan {plan.id}.",
                details={
                    "trade_plan_id": str(plan.id),
                    "symbol": order_intent.symbol,
                    "side": order_intent.side.value,
                    "order_type": order_intent.order_type.value,
                    "quantity": str(order_intent.quantity),
                    "limit_price": None
                    if order_intent.limit_price is None
                    else str(order_intent.limit_price),
                    "stop_price": None
                    if order_intent.stop_price is None
                    else str(order_intent.stop_price),
                    "status": order_intent.status.value,
                },
            )
        )
        return order_intent
