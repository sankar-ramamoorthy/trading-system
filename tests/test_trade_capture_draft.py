from trading_system.services.trade_capture_draft import (
    DraftFieldIssue,
    TradeCaptureDraft,
    TradeIdeaDraft,
    TradePlanDraft,
    TradeThesisDraft,
    optional_draft_fields,
    required_draft_fields,
)


def test_empty_trade_capture_draft_reports_required_fields_missing() -> None:
    draft = TradeCaptureDraft()

    issues = draft.validation_issues()

    assert not draft.is_ready_to_save()
    assert [issue.path for issue in issues] == [
        "TradeIdea.instrument_symbol",
        "TradeIdea.playbook_slug",
        "TradeIdea.purpose",
        "TradeIdea.direction",
        "TradeIdea.horizon",
        "TradeThesis.reasoning",
        "TradePlan.entry_criteria",
        "TradePlan.invalidation",
    ]
    assert {issue.issue_type for issue in issues} == {"missing"}


def test_complete_required_trade_capture_draft_is_ready_to_save() -> None:
    draft = _complete_required_draft()

    assert draft.validation_issues() == []
    assert draft.is_ready_to_save()


def test_optional_trade_capture_fields_do_not_block_save_readiness() -> None:
    draft = _complete_required_draft(
        thesis=TradeThesisDraft(
            reasoning="Trend remains intact after a controlled pullback.",
            supporting_evidence=["Holding the 20DMA"],
            risks=["Earnings gap risk"],
            disconfirming_signals=["Heavy distribution day"],
        ),
        plan=TradePlanDraft(
            entry_criteria="Buy on reclaim of prior high.",
            invalidation="Close below pullback low.",
            targets=["Prior high", "Measured move"],
            risk_model="Defined stop with fixed risk.",
            sizing_assumptions="Half size until confirmation.",
        ),
    )

    assert [definition.path for definition in optional_draft_fields()] == [
        "TradeThesis.supporting_evidence",
        "TradeThesis.risks",
        "TradeThesis.disconfirming_signals",
        "TradePlan.targets",
        "TradePlan.risk_model",
        "TradePlan.sizing_assumptions",
    ]
    assert draft.validation_issues() == []
    assert draft.is_ready_to_save()


def test_blank_required_strings_count_as_missing() -> None:
    draft = _complete_required_draft(
        idea=TradeIdeaDraft(
            instrument_symbol=" ",
            playbook_slug="pullback-to-trend",
            purpose="swing",
            direction="long",
            horizon="days_to_weeks",
        ),
        thesis=TradeThesisDraft(reasoning="\t"),
    )

    issues = draft.validation_issues()

    assert not draft.is_ready_to_save()
    assert [issue.path for issue in issues] == [
        "TradeIdea.instrument_symbol",
        "TradeThesis.reasoning",
    ]


def test_ambiguous_field_issue_blocks_save_and_preserves_candidates() -> None:
    issue = DraftFieldIssue(
        entity="TradeIdea",
        field="direction",
        issue_type="ambiguous",
        message="Direction could not be resolved cleanly.",
        candidates=("long", "short"),
    )
    draft = _complete_required_draft(ambiguous_field_issues=[issue])

    issues = draft.validation_issues()

    assert not draft.is_ready_to_save()
    assert issues == [issue]
    assert issues[0].path == "TradeIdea.direction"
    assert issues[0].candidates == ("long", "short")


def test_required_and_optional_field_definitions_expose_stable_paths() -> None:
    required_paths = [definition.path for definition in required_draft_fields()]
    optional_paths = [definition.path for definition in optional_draft_fields()]

    assert required_paths == [
        "TradeIdea.instrument_symbol",
        "TradeIdea.playbook_slug",
        "TradeIdea.purpose",
        "TradeIdea.direction",
        "TradeIdea.horizon",
        "TradeThesis.reasoning",
        "TradePlan.entry_criteria",
        "TradePlan.invalidation",
    ]
    assert optional_paths == [
        "TradeThesis.supporting_evidence",
        "TradeThesis.risks",
        "TradeThesis.disconfirming_signals",
        "TradePlan.targets",
        "TradePlan.risk_model",
        "TradePlan.sizing_assumptions",
    ]


def _complete_required_draft(
    *,
    idea: TradeIdeaDraft | None = None,
    thesis: TradeThesisDraft | None = None,
    plan: TradePlanDraft | None = None,
    ambiguous_field_issues: list[DraftFieldIssue] | None = None,
) -> TradeCaptureDraft:
    return TradeCaptureDraft(
        idea=idea
        or TradeIdeaDraft(
            instrument_symbol="NVDA",
            playbook_slug="pullback-to-trend",
            purpose="swing",
            direction="long",
            horizon="days_to_weeks",
        ),
        thesis=thesis
        or TradeThesisDraft(
            reasoning="Trend remains intact after a controlled pullback."
        ),
        plan=plan
        or TradePlanDraft(
            entry_criteria="Buy on reclaim of prior high.",
            invalidation="Close below pullback low.",
        ),
        source_text="NVDA long swing pullback setup.",
        ambiguous_field_issues=list(ambiguous_field_issues or []),
    )
