from fastapi.testclient import TestClient

from trading_system.app.api import create_app
from trading_system.infrastructure.json.repositories import build_json_repositories
from trading_system.services.trade_capture_draft import (
    TradeCaptureDraft,
    TradeIdeaDraft,
    TradePlanDraft,
    TradeThesisDraft,
)
from trading_system.services.trade_capture_parser import (
    FakeTradeCaptureParser,
    TradeCaptureParseError,
)


def test_trade_capture_parse_returns_draft_and_readiness(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    parser = FakeTradeCaptureParser(_complete_draft())
    client = TestClient(create_app(repositories=repositories, trade_capture_parser=parser))

    response = client.post(
        "/trade-capture/parse",
        json={"source_text": "NVDA long swing pullback setup."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["draft"]["idea"]["instrument_symbol"] == "NVDA"
    assert body["draft"]["idea"]["playbook_slug"] == "pullback-to-trend"
    assert body["draft"]["source_text"] == "NVDA long swing pullback setup."
    assert body["validation_issues"] == []
    assert body["ready_to_save"] is True


def test_trade_capture_parse_surfaces_missing_field_paths(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    parser = FakeTradeCaptureParser(
        TradeCaptureDraft(idea=TradeIdeaDraft(instrument_symbol="NVDA"))
    )
    client = TestClient(create_app(repositories=repositories, trade_capture_parser=parser))

    response = client.post(
        "/trade-capture/parse",
        json={"source_text": "NVDA setup."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ready_to_save"] is False
    assert [issue["path"] for issue in body["validation_issues"]] == [
        "TradeIdea.playbook_slug",
        "TradeIdea.purpose",
        "TradeIdea.direction",
        "TradeIdea.horizon",
        "TradeThesis.reasoning",
        "TradePlan.entry_criteria",
        "TradePlan.invalidation",
    ]


def test_trade_capture_parse_failure_returns_400(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(
        create_app(
            repositories=repositories,
            trade_capture_parser=_FailingParser("provider unavailable"),
        )
    )

    response = client.post(
        "/trade-capture/parse",
        json={"source_text": "NVDA setup."},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "provider unavailable"


def test_trade_capture_parse_does_not_write_json_records(tmp_path) -> None:
    store_path = tmp_path / "store.json"
    repositories = build_json_repositories(store_path)
    parser = FakeTradeCaptureParser(_complete_draft())
    client = TestClient(create_app(repositories=repositories, trade_capture_parser=parser))

    response = client.post(
        "/trade-capture/parse",
        json={"source_text": "NVDA long swing pullback setup."},
    )

    assert response.status_code == 200
    assert not store_path.exists()


def test_trade_capture_save_creates_linked_records_and_retrieves_summary(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))

    save_response = client.post("/trade-capture/save", json=_complete_draft_payload())

    assert save_response.status_code == 200
    saved = save_response.json()
    assert saved["trade_idea_id"]
    assert saved["trade_thesis_id"]
    assert saved["trade_plan_id"]
    assert saved["instrument_id"] == "33333333-3333-4333-8333-333333333333"
    assert saved["playbook_id"] == "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    assert saved["approval_state"] == "draft"

    retrieve_response = client.get(f"/trade-capture/saved/{saved['trade_plan_id']}")

    assert retrieve_response.status_code == 200
    assert retrieve_response.json() == saved
    assert len(repositories.ideas.list_all()) == 1
    assert len(repositories.theses.list_all()) == 1
    assert len(repositories.plans.list_all()) == 1
    assert repositories.plans.list_all()[0].approval_state == "draft"


def test_trade_capture_save_rejects_missing_required_fields(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))
    payload = _complete_draft_payload()
    payload["idea"]["instrument_symbol"] = " "
    payload["thesis"]["reasoning"] = None

    response = client.post("/trade-capture/save", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "Trade capture draft is not ready to save."
    assert [issue["path"] for issue in detail["issues"]] == [
        "TradeIdea.instrument_symbol",
        "TradeThesis.reasoning",
    ]
    assert repositories.ideas.list_all() == []


def test_trade_capture_save_rejects_ambiguous_draft(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))
    payload = _complete_draft_payload()
    payload["ambiguous_field_issues"] = [
        {
            "entity": "TradeIdea",
            "field": "direction",
            "path": "TradeIdea.direction",
            "issue_type": "ambiguous",
            "message": "Direction is unclear.",
            "candidates": ["long", "short"],
        }
    ]

    response = client.post("/trade-capture/save", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert [issue["path"] for issue in detail["issues"]] == ["TradeIdea.direction"]
    assert detail["issues"][0]["candidates"] == ["long", "short"]
    assert repositories.ideas.list_all() == []


def test_trade_capture_save_rejects_unknown_symbol_or_playbook(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))
    payload = _complete_draft_payload()
    payload["idea"]["instrument_symbol"] = "XYZ"

    response = client.post("/trade-capture/save", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "message": "Unknown instrument symbol: XYZ",
        "issues": [],
    }
    assert repositories.ideas.list_all() == []


def test_trade_capture_saved_result_rejects_unknown_plan_id(tmp_path) -> None:
    repositories = build_json_repositories(tmp_path / "store.json")
    client = TestClient(create_app(repositories=repositories))

    response = client.get(
        "/trade-capture/saved/00000000-0000-4000-8000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Trade plan does not exist."


class _FailingParser:
    def __init__(self, message: str) -> None:
        self._message = message

    def parse(self, source_text: str) -> TradeCaptureDraft:
        raise TradeCaptureParseError(self._message)


def _complete_draft() -> TradeCaptureDraft:
    return TradeCaptureDraft(
        idea=TradeIdeaDraft(
            instrument_symbol="NVDA",
            playbook_slug="pullback-to-trend",
            purpose="swing",
            direction="long",
            horizon="days_to_weeks",
        ),
        thesis=TradeThesisDraft(
            reasoning="Trend remains intact after a controlled pullback.",
            supporting_evidence=["Holding the 20DMA"],
            risks=["Earnings gap risk"],
            disconfirming_signals=["Heavy distribution day"],
        ),
        plan=TradePlanDraft(
            entry_criteria="Buy on reclaim of prior high.",
            invalidation="Close below pullback low.",
            targets=["Prior high"],
            risk_model="Defined stop with fixed risk.",
            sizing_assumptions="Half size until confirmation.",
        ),
        ambiguous_field_issues=[],
    )


def _complete_draft_payload() -> dict:
    return {
        "idea": {
            "instrument_symbol": "NVDA",
            "playbook_slug": "pullback-to-trend",
            "purpose": "swing",
            "direction": "long",
            "horizon": "days_to_weeks",
        },
        "thesis": {
            "reasoning": "Trend remains intact after a controlled pullback.",
            "supporting_evidence": ["Holding the 20DMA"],
            "risks": ["Earnings gap risk"],
            "disconfirming_signals": ["Heavy distribution day"],
        },
        "plan": {
            "entry_criteria": "Buy on reclaim of prior high.",
            "invalidation": "Close below pullback low.",
            "targets": ["Prior high"],
            "risk_model": "Defined stop with fixed risk.",
            "sizing_assumptions": "Half size until confirmation.",
        },
        "source_text": "NVDA long swing pullback setup.",
        "ambiguous_field_issues": [],
    }
