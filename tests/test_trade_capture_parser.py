from types import SimpleNamespace

import pytest

from trading_system.infrastructure.litellm.trade_capture_parser import (
    LiteLLMTradeCaptureParser,
    LiteLLMTradeCaptureParserConfig,
)
from trading_system.services.trade_capture_draft import (
    DraftFieldIssue,
    TradeCaptureDraft,
    TradeIdeaDraft,
    TradePlanDraft,
    TradeThesisDraft,
)
from trading_system.services.trade_capture_parser import (
    FakeTradeCaptureParser,
    TradeCaptureParseError,
)


def test_fake_trade_capture_parser_returns_configured_draft() -> None:
    draft = TradeCaptureDraft(
        idea=TradeIdeaDraft(instrument_symbol="NVDA"),
        thesis=TradeThesisDraft(reasoning="Trend remains intact."),
        plan=TradePlanDraft(entry_criteria="Buy reclaim."),
    )
    parser = FakeTradeCaptureParser(draft)

    parsed = parser.parse("NVDA long swing setup.")

    assert parsed is draft
    assert parsed.source_text == "NVDA long swing setup."


def test_fake_trade_capture_parser_rejects_blank_text() -> None:
    parser = FakeTradeCaptureParser()

    with pytest.raises(TradeCaptureParseError, match="Trade capture text is required"):
        parser.parse(" ")


def test_litellm_parser_maps_valid_json_to_trade_capture_draft(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        "trading_system.infrastructure.litellm.trade_capture_parser.import_module",
        lambda name: SimpleNamespace(completion=_completion(calls, _valid_json())),
    )

    parser = _parser()
    draft = parser.parse("NVDA long swing pullback-to-trend setup.")

    assert draft.source_text == "NVDA long swing pullback-to-trend setup."
    assert draft.idea.instrument_symbol == "NVDA"
    assert draft.idea.playbook_slug == "pullback-to-trend"
    assert draft.thesis.supporting_evidence == ["Holding the 20DMA"]
    assert draft.plan.targets == ["Prior high"]
    assert draft.validation_issues() == []
    assert calls[0]["model"] == "ollama_chat/llama3.1"
    assert calls[0]["api_base"] == "http://localhost:11434"
    assert calls[0]["response_format"] == {"type": "json_object"}


def test_litellm_parser_preserves_missing_required_field_issues(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.infrastructure.litellm.trade_capture_parser.import_module",
        lambda name: SimpleNamespace(
            completion=_completion([], '{"idea": {"instrument_symbol": "NVDA"}}')
        ),
    )

    draft = _parser().parse("NVDA setup with missing detail.")

    assert [issue.path for issue in draft.validation_issues()] == [
        "TradeIdea.playbook_slug",
        "TradeIdea.purpose",
        "TradeIdea.direction",
        "TradeIdea.horizon",
        "TradeThesis.reasoning",
        "TradePlan.entry_criteria",
        "TradePlan.invalidation",
    ]


def test_litellm_parser_preserves_ambiguous_field_issues(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.infrastructure.litellm.trade_capture_parser.import_module",
        lambda name: SimpleNamespace(
            completion=_completion(
                [],
                """
                {
                  "idea": {
                    "instrument_symbol": "NVDA",
                    "playbook_slug": "pullback-to-trend",
                    "purpose": "swing",
                    "direction": "long",
                    "horizon": "days_to_weeks"
                  },
                  "thesis": {"reasoning": "Trend remains intact."},
                  "plan": {
                    "entry_criteria": "Buy reclaim.",
                    "invalidation": "Close below low."
                  },
                  "ambiguous_fields": [
                    {
                      "entity": "TradeIdea",
                      "field": "direction",
                      "message": "Direction could be either long or short.",
                      "candidates": ["long", "short"]
                    }
                  ]
                }
                """,
            )
        ),
    )

    draft = _parser().parse("NVDA setup, unclear direction.")

    assert draft.validation_issues() == [
        DraftFieldIssue(
            entity="TradeIdea",
            field="direction",
            issue_type="ambiguous",
            message="Direction could be either long or short.",
            candidates=("long", "short"),
        )
    ]
    assert not draft.is_ready_to_save()


def test_litellm_parser_rejects_blank_text_before_provider_call(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        "trading_system.infrastructure.litellm.trade_capture_parser.import_module",
        lambda name: SimpleNamespace(completion=_completion(calls, _valid_json())),
    )

    with pytest.raises(TradeCaptureParseError, match="Trade capture text is required"):
        _parser().parse("\t")

    assert calls == []


def test_litellm_parser_config_requires_model_and_api_base(monkeypatch) -> None:
    monkeypatch.delenv("TRADING_SYSTEM_LLM_MODEL", raising=False)
    monkeypatch.delenv("TRADING_SYSTEM_LLM_API_BASE", raising=False)

    with pytest.raises(TradeCaptureParseError, match="TRADING_SYSTEM_LLM_MODEL"):
        LiteLLMTradeCaptureParserConfig.from_env()

    with pytest.raises(TradeCaptureParseError, match="TRADING_SYSTEM_LLM_MODEL"):
        LiteLLMTradeCaptureParser(
            LiteLLMTradeCaptureParserConfig(model="", api_base="http://localhost:11434")
        )
    with pytest.raises(TradeCaptureParseError, match="TRADING_SYSTEM_LLM_API_BASE"):
        LiteLLMTradeCaptureParser(
            LiteLLMTradeCaptureParserConfig(model="ollama_chat/llama3.1", api_base="")
        )


def test_litellm_parser_config_loads_from_env(monkeypatch) -> None:
    monkeypatch.setenv("TRADING_SYSTEM_LLM_MODEL", "ollama_chat/llama3.1")
    monkeypatch.setenv("TRADING_SYSTEM_LLM_API_BASE", "http://localhost:11434")

    config = LiteLLMTradeCaptureParserConfig.from_env()

    assert config == LiteLLMTradeCaptureParserConfig(
        model="ollama_chat/llama3.1",
        api_base="http://localhost:11434",
    )


def test_litellm_parser_wraps_provider_failure(monkeypatch) -> None:
    def failing_completion(**kwargs):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(
        "trading_system.infrastructure.litellm.trade_capture_parser.import_module",
        lambda name: SimpleNamespace(completion=failing_completion),
    )

    with pytest.raises(
        TradeCaptureParseError,
        match="Trade capture parser provider call failed",
    ):
        _parser().parse("NVDA setup.")


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not json", "invalid JSON"),
        ("[]", "JSON must be an object"),
        ('{"idea": []}', "field 'idea' must be an object"),
        ('{"ambiguous_fields": {}}', "field 'ambiguous_fields' must be a list"),
        ('{"thesis": {"risks": ["ok", 1]}}', "field 'risks' must contain only strings"),
        ('{"ambiguous_fields": [{"entity": "Bad", "field": "direction", "message": "bad"}]}', "ambiguity entity is invalid"),
    ],
)
def test_litellm_parser_rejects_malformed_payloads(
    monkeypatch,
    content: str,
    message: str,
) -> None:
    monkeypatch.setattr(
        "trading_system.infrastructure.litellm.trade_capture_parser.import_module",
        lambda name: SimpleNamespace(completion=_completion([], content)),
    )

    with pytest.raises(TradeCaptureParseError, match=message):
        _parser().parse("NVDA setup.")


def test_litellm_parser_rejects_malformed_provider_response(monkeypatch) -> None:
    monkeypatch.setattr(
        "trading_system.infrastructure.litellm.trade_capture_parser.import_module",
        lambda name: SimpleNamespace(
            completion=lambda **kwargs: SimpleNamespace(choices=[])
        ),
    )

    with pytest.raises(TradeCaptureParseError, match="response was malformed"):
        _parser().parse("NVDA setup.")


def _parser() -> LiteLLMTradeCaptureParser:
    return LiteLLMTradeCaptureParser(
        LiteLLMTradeCaptureParserConfig(
            model="ollama_chat/llama3.1",
            api_base="http://localhost:11434",
        )
    )


def _completion(calls, content: str):
    def completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                )
            ]
        )

    return completion


def _valid_json() -> str:
    return """
    {
      "idea": {
        "instrument_symbol": "NVDA",
        "playbook_slug": "pullback-to-trend",
        "purpose": "swing",
        "direction": "long",
        "horizon": "days_to_weeks"
      },
      "thesis": {
        "reasoning": "Trend remains intact after a controlled pullback.",
        "supporting_evidence": ["Holding the 20DMA"],
        "risks": ["Earnings gap risk"],
        "disconfirming_signals": ["Heavy distribution day"]
      },
      "plan": {
        "entry_criteria": "Buy on reclaim of prior high.",
        "invalidation": "Close below pullback low.",
        "targets": ["Prior high"],
        "risk_model": "Defined stop with fixed risk.",
        "sizing_assumptions": "Half size until confirmation."
      },
      "ambiguous_fields": []
    }
    """
