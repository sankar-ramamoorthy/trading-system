"""Tests for the Alpaca paper broker adapter."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from trading_system.domain.trading.broker_order import BrokerOrderStatus
from trading_system.domain.trading.order_intent import OrderIntent, OrderSide, OrderType
from trading_system.domain.trading.position import Position
from trading_system.infrastructure.broker import AlpacaPaperBrokerClient
from trading_system.infrastructure.local_secret_vault import LocalSecretVaultError


def test_alpaca_submit_maps_limit_order_request_and_response() -> None:
    """Submitting through Alpaca builds a paper order request from local intent."""
    now = datetime(2026, 5, 3, tzinfo=UTC)
    fake_client = _FakeTradingClient(
        submitted_order=SimpleNamespace(
            id="alpaca-order-1",
            status="new",
            submitted_at=now,
            updated_at=now,
        )
    )
    order_intent = _order_intent(
        order_type=OrderType.LIMIT,
        limit_price=Decimal("25.50"),
    )

    submission = AlpacaPaperBrokerClient(trading_client=fake_client).submit_order(
        order_intent,
        _position(order_intent.trade_plan_id),
    )

    request = fake_client.submitted_requests[0]
    assert request.__class__.__name__ == "LimitOrderRequest"
    assert request.symbol == "AAPL"
    assert Decimal(str(request.qty)) == Decimal("100")
    assert str(request.side.value) == "buy"
    assert str(request.time_in_force.value) == "day"
    assert request.client_order_id == f"ts-{order_intent.id}"
    assert Decimal(str(request.limit_price)) == Decimal("25.5")
    assert submission.provider == "alpaca"
    assert submission.provider_order_id == "alpaca-order-1"
    assert submission.status == BrokerOrderStatus.SUBMITTED


@pytest.mark.parametrize(
    ("order_type", "limit_price", "stop_price", "expected_request"),
    [
        (OrderType.MARKET, None, None, "MarketOrderRequest"),
        (OrderType.STOP, None, Decimal("24"), "StopOrderRequest"),
        (OrderType.STOP_LIMIT, Decimal("25"), Decimal("24"), "StopLimitOrderRequest"),
    ],
)
def test_alpaca_submit_maps_supported_order_types(
    order_type: OrderType,
    limit_price: Decimal | None,
    stop_price: Decimal | None,
    expected_request: str,
) -> None:
    """The adapter supports the local order types accepted by OrderIntent."""
    fake_client = _FakeTradingClient()
    order_intent = _order_intent(
        order_type=order_type,
        limit_price=limit_price,
        stop_price=stop_price,
    )

    AlpacaPaperBrokerClient(trading_client=fake_client).submit_order(
        order_intent,
        _position(order_intent.trade_plan_id),
    )

    assert fake_client.submitted_requests[0].__class__.__name__ == expected_request


@pytest.mark.parametrize(
    ("alpaca_status", "expected_status"),
    [
        ("filled", BrokerOrderStatus.FILLED),
        ("canceled", BrokerOrderStatus.CANCELED),
        ("expired", BrokerOrderStatus.CANCELED),
        ("done_for_day", BrokerOrderStatus.CANCELED),
        ("rejected", BrokerOrderStatus.REJECTED),
        ("suspended", BrokerOrderStatus.REJECTED),
        ("partially_filled", BrokerOrderStatus.SUBMITTED),
        ("accepted", BrokerOrderStatus.SUBMITTED),
    ],
)
def test_alpaca_sync_maps_statuses(
    alpaca_status: str,
    expected_status: BrokerOrderStatus,
) -> None:
    """Alpaca status values collapse into the local broker-order lifecycle."""
    fake_client = _FakeTradingClient(
        synced_order=SimpleNamespace(
            id="alpaca-order-1",
            status=alpaca_status,
            updated_at=datetime(2026, 5, 3, tzinfo=UTC),
            filled_avg_price="25.75" if alpaca_status == "filled" else None,
        )
    )

    result = AlpacaPaperBrokerClient(trading_client=fake_client).sync_order(
        "alpaca-order-1"
    )

    assert result.status == expected_status
    if expected_status == BrokerOrderStatus.FILLED:
        assert result.fill_price == Decimal("25.75")
    else:
        assert result.fill_price is None


def test_alpaca_sync_rejects_simulated_fill_price() -> None:
    """Alpaca sync must not use the simulated fill-price test hook."""
    with pytest.raises(ValueError, match="not used for Alpaca"):
        AlpacaPaperBrokerClient(trading_client=_FakeTradingClient()).sync_order(
            "alpaca-order-1",
            simulated_fill_price=Decimal("25.50"),
        )


def test_alpaca_client_resolves_required_credentials(monkeypatch, tmp_path) -> None:
    """The adapter requires the reserved Alpaca secret names."""
    import trading_system.infrastructure.local_secret_vault as secret_vault

    monkeypatch.setattr(secret_vault, "DEFAULT_VAULT_PATH", tmp_path / "keys.enc")
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)

    with pytest.raises(LocalSecretVaultError, match="ALPACA_API_KEY is required"):
        AlpacaPaperBrokerClient()._trading_client()


class _FakeTradingClient:
    def __init__(
        self,
        *,
        submitted_order=None,
        synced_order=None,
    ) -> None:
        now = datetime(2026, 5, 3, tzinfo=UTC)
        self.submitted_order = submitted_order or SimpleNamespace(
            id="alpaca-order-1",
            status="new",
            submitted_at=now,
            updated_at=now,
        )
        self.synced_order = synced_order or SimpleNamespace(
            id="alpaca-order-1",
            status="filled",
            updated_at=now,
            filled_avg_price="25.50",
        )
        self.submitted_requests = []

    def submit_order(self, *, order_data):
        self.submitted_requests.append(order_data)
        return self.submitted_order

    def get_order_by_id(self, order_id):
        assert order_id == "alpaca-order-1"
        return self.synced_order


def _order_intent(
    *,
    order_type: OrderType,
    limit_price: Decimal | None = None,
    stop_price: Decimal | None = None,
) -> OrderIntent:
    return OrderIntent(
        trade_plan_id=uuid4(),
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=order_type,
        quantity=Decimal("100"),
        limit_price=limit_price,
        stop_price=stop_price,
    )


def _position(trade_plan_id):
    return Position(
        trade_plan_id=trade_plan_id,
        instrument_id=uuid4(),
        purpose="swing",
        opened_at=datetime(2026, 5, 3, tzinfo=UTC),
    )
