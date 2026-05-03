from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from trading_system.app.api import create_app
from trading_system.domain.rules.rule_evaluation import RuleEvaluation
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.order_intent import OrderIntent, OrderSide, OrderType
from trading_system.domain.trading.position import Position
from trading_system.infrastructure.json.repositories import build_json_repositories


NVDA_ID = UUID("33333333-3333-4333-8333-333333333333")
AAPL_ID = UUID("11111111-1111-4111-8111-111111111111")


def test_list_trade_plans_supports_filters_sort_and_display_labels(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))
    first = _save_plan(client, symbol="NVDA")
    second = _save_plan(client, symbol="AAPL")
    client.post(f"/trade-plans/{first}/approve")

    all_response = client.get("/trade-plans?sort=newest")
    approved_response = client.get("/trade-plans?approval_state=approved")
    draft_response = client.get("/trade-plans?approval_state=draft")

    assert all_response.status_code == 200
    all_items = all_response.json()
    assert [item["id"] for item in all_items] == [str(second), str(first)]
    assert all_items[0]["instrument_symbol"] == "AAPL"
    assert all_items[0]["playbook_slug"] == "pullback-to-trend"
    assert all_items[0]["linked_context_count"] == 0
    assert [item["id"] for item in approved_response.json()] == [str(first)]
    assert [item["id"] for item in draft_response.json()] == [str(second)]


def test_get_trade_plan_detail_includes_linked_records_and_context_metadata_only(
    tmp_path,
) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))
    plan_id = _save_plan(client, symbol="NVDA")
    repositories.evaluations.add(
        RuleEvaluation(
            rule_id=uuid4(),
            entity_type="TradePlan",
            entity_id=plan_id,
            passed=True,
            details="Risk is defined.",
        )
    )
    repositories.order_intents.add(
        OrderIntent(
            trade_plan_id=plan_id,
            symbol="NVDA",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("10"),
            limit_price=Decimal("100"),
        )
    )
    repositories.positions.add(
        Position(
            trade_plan_id=plan_id,
            instrument_id=NVDA_ID,
            purpose="swing",
            current_quantity=Decimal("10"),
            average_entry_price=Decimal("100"),
        )
    )
    repositories.market_context_snapshots.add(
        MarketContextSnapshot(
            instrument_id=NVDA_ID,
            target_type="TradePlan",
            target_id=plan_id,
            context_type="daily_bars",
            source="yfinance",
            source_ref="NVDA",
            observed_at=datetime(2026, 5, 1, 16, 0, tzinfo=UTC),
            payload={"bars": [{"close": 100}]},
        )
    )

    response = client.get(f"/trade-plans/{plan_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["idea"]["instrument_symbol"] == "NVDA"
    assert body["thesis"]["reasoning"] == "Trend remains intact."
    assert body["plan"]["entry_criteria"] == "Buy reclaim."
    assert len(body["rule_evaluations"]) == 1
    assert len(body["order_intents"]) == 1
    assert len(body["positions"]) == 1
    assert len(body["market_context"]) == 1
    assert body["market_context"][0]["context_type"] == "daily_bars"
    assert "payload" not in body["market_context"][0]


def test_approve_trade_plan_persists_state_and_missing_plan_returns_404(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))
    plan_id = _save_plan(client, symbol="NVDA")

    response = client.post(f"/trade-plans/{plan_id}/approve")
    missing_response = client.post(
        "/trade-plans/00000000-0000-4000-8000-000000000000/approve"
    )

    assert response.status_code == 200
    assert response.json()["plan"]["approval_state"] == "approved"
    assert repositories.plans.get(plan_id).approval_state == "approved"
    assert missing_response.status_code == 404


def test_missing_trade_plan_detail_returns_404(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))

    response = client.get("/trade-plans/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "Trade plan does not exist."


def test_list_market_context_supports_metadata_filters(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))
    plan_id = _save_plan(client, symbol="NVDA")
    linked = _add_snapshot(
        repositories,
        instrument_id=NVDA_ID,
        target_type="TradePlan",
        target_id=plan_id,
        context_type="daily_bars",
        source="yfinance",
    )
    _add_snapshot(
        repositories,
        instrument_id=AAPL_ID,
        target_type=None,
        target_id=None,
        context_type="options_chain",
        source="yfinance",
    )

    instrument_response = client.get(f"/market-context?instrument_id={NVDA_ID}")
    target_response = client.get(
        f"/market-context?target_type=TradePlan&target_id={plan_id}"
    )
    context_type_response = client.get("/market-context?context_type=options_chain")

    assert [item["id"] for item in instrument_response.json()] == [str(linked.id)]
    assert [item["id"] for item in target_response.json()] == [str(linked.id)]
    assert context_type_response.json()[0]["instrument_id"] == str(AAPL_ID)
    assert "payload" not in instrument_response.json()[0]


def test_copy_market_context_to_trade_plan_preserves_original_and_rejects_mismatch(
    tmp_path,
) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))
    nvda_plan_id = _save_plan(client, symbol="NVDA")
    aapl_plan_id = _save_plan(client, symbol="AAPL")
    original = _add_snapshot(
        repositories,
        instrument_id=NVDA_ID,
        target_type=None,
        target_id=None,
        context_type="daily_bars",
        source="yfinance",
    )

    response = client.post(
        f"/market-context/{original.id}/copy-to-target",
        json={"target_type": "TradePlan", "target_id": str(nvda_plan_id)},
    )
    mismatch_response = client.post(
        f"/market-context/{original.id}/copy-to-target",
        json={"target_type": "TradePlan", "target_id": str(aapl_plan_id)},
    )

    assert response.status_code == 200
    copied = response.json()
    assert copied["id"] != str(original.id)
    assert copied["target_type"] == "TradePlan"
    assert copied["target_id"] == str(nvda_plan_id)
    assert repositories.market_context_snapshots.get(original.id).target_type is None
    assert mismatch_response.status_code == 400
    assert mismatch_response.json()["detail"] == "Instrument id does not match the context target."


def _save_plan(client: TestClient, *, symbol: str):
    response = client.post("/trade-capture/save", json=_draft_payload(symbol=symbol))
    assert response.status_code == 200
    return UUID(response.json()["trade_plan_id"])


def _add_snapshot(
    repositories,
    *,
    instrument_id,
    target_type,
    target_id,
    context_type,
    source,
) -> MarketContextSnapshot:
    snapshot = MarketContextSnapshot(
        instrument_id=instrument_id,
        target_type=target_type,
        target_id=target_id,
        context_type=context_type,
        source=source,
        observed_at=datetime(2026, 5, 1, 16, 0, tzinfo=UTC),
        payload={"sample": True},
    )
    repositories.market_context_snapshots.add(snapshot)
    return snapshot


def _draft_payload(*, symbol: str) -> dict:
    return {
        "idea": {
            "instrument_symbol": symbol,
            "playbook_slug": "pullback-to-trend",
            "purpose": "swing",
            "direction": "long",
            "horizon": "days_to_weeks",
        },
        "thesis": {
            "reasoning": "Trend remains intact.",
            "supporting_evidence": ["Higher low"],
            "risks": ["Market weakness"],
            "disconfirming_signals": ["Breaks support"],
        },
        "plan": {
            "entry_criteria": "Buy reclaim.",
            "invalidation": "Close below low.",
            "targets": ["Prior high"],
            "risk_model": "Defined stop.",
            "sizing_assumptions": "Half size.",
        },
        "source_text": f"{symbol} setup.",
        "ambiguous_field_issues": [],
    }
