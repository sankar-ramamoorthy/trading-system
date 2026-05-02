"""Application workflows for API-first trade capture."""

from dataclasses import dataclass
from uuid import UUID

from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.thesis import TradeThesis
from trading_system.ports.trade_capture_parser import TradeCaptureParser
from trading_system.services.reference_lookup_service import ReferenceLookupService
from trading_system.services.trade_capture_draft import DraftFieldIssue, TradeCaptureDraft
from trading_system.services.trade_capture_parser import TradeCaptureParseError
from trading_system.services.trade_planning_service import TradePlanningService
from trading_system.services.trade_query_service import TradeQueryService


@dataclass(frozen=True)
class SavedTradeCapture:
    """Linked records created from one confirmed trade-capture draft."""

    trade_idea: TradeIdea
    trade_thesis: TradeThesis
    trade_plan: TradePlan


class TradeCaptureValidationError(ValueError):
    """Raised when a draft cannot be saved as confirmed trade records."""

    def __init__(self, message: str, issues: list[DraftFieldIssue] | None = None) -> None:
        super().__init__(message)
        self.issues = list(issues or [])


class TradeCaptureService:
    """Coordinates parsing, saving, and retrieval for API trade capture."""

    def __init__(
        self,
        *,
        parser: TradeCaptureParser,
        reference_lookup: ReferenceLookupService,
        planning: TradePlanningService,
        queries: TradeQueryService,
    ) -> None:
        self._parser = parser
        self._reference_lookup = reference_lookup
        self._planning = planning
        self._queries = queries

    def parse(self, source_text: str) -> TradeCaptureDraft:
        """Parse source text into an editable draft without persistence."""
        try:
            return self._parser.parse(source_text)
        except TradeCaptureParseError:
            raise

    def save_confirmed_draft(self, draft: TradeCaptureDraft) -> SavedTradeCapture:
        """Persist linked idea, thesis, and plan records from a confirmed draft."""
        issues = draft.validation_issues()
        if issues:
            raise TradeCaptureValidationError(
                "Trade capture draft is not ready to save.",
                issues,
            )

        assert draft.idea.instrument_symbol is not None
        assert draft.idea.playbook_slug is not None
        assert draft.idea.purpose is not None
        assert draft.idea.direction is not None
        assert draft.idea.horizon is not None
        assert draft.thesis.reasoning is not None
        assert draft.plan.entry_criteria is not None
        assert draft.plan.invalidation is not None

        try:
            instrument = self._reference_lookup.resolve_instrument(
                draft.idea.instrument_symbol
            )
            playbook = self._reference_lookup.resolve_playbook(draft.idea.playbook_slug)
        except ValueError as exc:
            raise TradeCaptureValidationError(str(exc)) from exc

        idea = self._planning.create_trade_idea(
            instrument_id=instrument.id,
            playbook_id=playbook.id,
            purpose=draft.idea.purpose,
            direction=draft.idea.direction,
            horizon=draft.idea.horizon,
        )
        thesis = self._planning.create_trade_thesis(
            trade_idea_id=idea.id,
            reasoning=draft.thesis.reasoning,
            supporting_evidence=draft.thesis.supporting_evidence,
            risks=draft.thesis.risks,
            disconfirming_signals=draft.thesis.disconfirming_signals,
        )
        plan = self._planning.create_trade_plan(
            trade_idea_id=idea.id,
            trade_thesis_id=thesis.id,
            entry_criteria=draft.plan.entry_criteria,
            invalidation=draft.plan.invalidation,
            targets=draft.plan.targets,
            risk_model=draft.plan.risk_model,
            sizing_assumptions=draft.plan.sizing_assumptions,
        )
        return SavedTradeCapture(trade_idea=idea, trade_thesis=thesis, trade_plan=plan)

    def get_saved_result(self, trade_plan_id: UUID) -> SavedTradeCapture:
        """Return saved trade-capture records by trade plan id."""
        detail = self._queries.get_trade_plan_detail(trade_plan_id)
        return SavedTradeCapture(
            trade_idea=detail.trade_idea,
            trade_thesis=detail.trade_thesis,
            trade_plan=detail.trade_plan,
        )
