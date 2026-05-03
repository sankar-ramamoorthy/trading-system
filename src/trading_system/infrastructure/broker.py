"""Broker adapter implementations for local paper execution workflows."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from trading_system.domain.trading.broker_order import BrokerOrderStatus
from trading_system.domain.trading.order_intent import OrderIntent, OrderSide, OrderType
from trading_system.domain.trading.position import Position
from trading_system.infrastructure.local_secret_vault import require_secret
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


class AlpacaPaperBrokerClient(BrokerClient):
    """Alpaca paper-trading adapter behind the local broker port."""

    provider = "alpaca"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        secret_key: str | None = None,
        trading_client: Any | None = None,
    ) -> None:
        self._client = trading_client
        self._api_key = api_key
        self._secret_key = secret_key

    def submit_order(
        self,
        order_intent: OrderIntent,
        position: Position,
    ) -> BrokerSubmission:
        """Submit the order intent to Alpaca paper trading."""
        client_order_id = f"ts-{order_intent.id}"
        order_request = self._build_order_request(order_intent, client_order_id)
        order = self._trading_client().submit_order(order_data=order_request)
        return BrokerSubmission(
            provider=self.provider,
            provider_order_id=str(_required_attr(order, "id")),
            status=_map_alpaca_status(_required_attr(order, "status")),
            submitted_at=_datetime_attr(order, "submitted_at") or datetime.now(UTC),
            updated_at=_datetime_attr(order, "updated_at") or datetime.now(UTC),
        )

    def sync_order(
        self,
        broker_order_id: str,
        simulated_fill_price: Decimal | None = None,
    ) -> BrokerOrderSync:
        """Fetch Alpaca's current order status and fill price when complete."""
        if simulated_fill_price is not None:
            raise ValueError("Simulated fill price is not used for Alpaca paper orders.")
        order = self._trading_client().get_order_by_id(broker_order_id)
        status = _map_alpaca_status(_required_attr(order, "status"))
        fill_price = _decimal_attr(order, "filled_avg_price")
        if status == BrokerOrderStatus.FILLED and fill_price is None:
            raise ValueError("Filled Alpaca order did not include an average fill price.")
        return BrokerOrderSync(
            status=status,
            updated_at=_datetime_attr(order, "updated_at") or datetime.now(UTC),
            fill_price=fill_price,
        )

    def _trading_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from alpaca.trading.client import TradingClient
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise ValueError("alpaca-py is required for Alpaca paper trading.") from exc
        api_key = self._api_key or require_secret("ALPACA_API_KEY")
        secret_key = self._secret_key or require_secret("ALPACA_SECRET_KEY")
        self._client = TradingClient(api_key, secret_key, paper=True)
        return self._client

    def _build_order_request(self, order_intent: OrderIntent, client_order_id: str) -> Any:
        try:
            from alpaca.trading.enums import OrderSide as AlpacaOrderSide
            from alpaca.trading.enums import TimeInForce
            from alpaca.trading.requests import (
                LimitOrderRequest,
                MarketOrderRequest,
                StopLimitOrderRequest,
                StopOrderRequest,
            )
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
            raise ValueError("alpaca-py is required for Alpaca paper trading.") from exc

        side = (
            AlpacaOrderSide.BUY
            if order_intent.side == OrderSide.BUY
            else AlpacaOrderSide.SELL
        )
        base = {
            "symbol": order_intent.symbol,
            "qty": float(order_intent.quantity),
            "side": side,
            "time_in_force": TimeInForce.DAY,
            "client_order_id": client_order_id,
        }
        if order_intent.order_type == OrderType.MARKET:
            return MarketOrderRequest(**base)
        if order_intent.order_type == OrderType.LIMIT:
            if order_intent.limit_price is None:
                raise ValueError("Limit price is required for Alpaca limit orders.")
            return LimitOrderRequest(
                **base,
                limit_price=float(order_intent.limit_price),
            )
        if order_intent.order_type == OrderType.STOP:
            if order_intent.stop_price is None:
                raise ValueError("Stop price is required for Alpaca stop orders.")
            return StopOrderRequest(
                **base,
                stop_price=float(order_intent.stop_price),
            )
        if order_intent.order_type == OrderType.STOP_LIMIT:
            if order_intent.limit_price is None or order_intent.stop_price is None:
                raise ValueError(
                    "Limit price and stop price are required for Alpaca stop-limit orders."
                )
            return StopLimitOrderRequest(
                **base,
                limit_price=float(order_intent.limit_price),
                stop_price=float(order_intent.stop_price),
            )
        raise ValueError(f"Unsupported Alpaca order type: {order_intent.order_type}.")


def _map_alpaca_status(status: Any) -> BrokerOrderStatus:
    value = str(getattr(status, "value", status)).lower()
    if value == "filled":
        return BrokerOrderStatus.FILLED
    if value in {"canceled", "cancelled", "expired", "done_for_day"}:
        return BrokerOrderStatus.CANCELED
    if value in {"rejected", "suspended"}:
        return BrokerOrderStatus.REJECTED
    return BrokerOrderStatus.SUBMITTED


def _required_attr(item: Any, name: str) -> Any:
    value = getattr(item, name, None)
    if value is None and isinstance(item, dict):
        value = item.get(name)
    if value is None:
        raise ValueError(f"Alpaca order response missing {name}.")
    return value


def _datetime_attr(item: Any, name: str) -> datetime | None:
    value = getattr(item, name, None)
    if value is None and isinstance(item, dict):
        value = item.get(name)
    return value if isinstance(value, datetime) else None


def _decimal_attr(item: Any, name: str) -> Decimal | None:
    value = getattr(item, name, None)
    if value is None and isinstance(item, dict):
        value = item.get(name)
    if value is None or value == "":
        return None
    return Decimal(str(value))
