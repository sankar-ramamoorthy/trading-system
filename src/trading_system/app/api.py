"""FastAPI entrypoint for local web workflows."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from trading_system.domain.trading.instrument import Instrument
from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.domain.trading.order_intent import OrderIntent
from trading_system.domain.trading.playbook import Playbook
from trading_system.domain.trading.position import Position
from trading_system.infrastructure.json.repositories import (
    JsonRepositorySet,
    build_json_repositories,
)
from trading_system.infrastructure.litellm.trade_capture_parser import (
    LiteLLMTradeCaptureParser,
    LiteLLMTradeCaptureParserConfig,
)
from trading_system.infrastructure.seeded_reference_data import (
    SeededReferenceDataRepository,
)
from trading_system.ports.reference_data import ReferenceDataRepository
from trading_system.ports.trade_capture_parser import TradeCaptureParser
from trading_system.services.market_context_service import (
    MarketContextImportService,
    MarketContextQueryService,
)
from trading_system.services.reference_lookup_service import ReferenceLookupService
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
from trading_system.services.trade_capture_service import (
    SavedTradeCapture,
    TradeCaptureService,
    TradeCaptureValidationError,
)
from trading_system.services.trade_planning_service import TradePlanningService
from trading_system.services.trade_query_service import TradePlanDetail, TradeQueryService


class InstrumentResponse(BaseModel):
    """API representation of a known instrument."""

    id: UUID
    symbol: str
    name: str | None


class PlaybookResponse(BaseModel):
    """API representation of a known playbook."""

    id: UUID
    slug: str
    name: str
    description: str | None


class DraftFieldIssueResponse(BaseModel):
    """API representation of a missing or ambiguous draft field."""

    entity: str
    field: str
    path: str
    issue_type: str
    message: str
    candidates: list[str] = Field(default_factory=list)


class TradeIdeaDraftPayload(BaseModel):
    """API payload for editable idea draft data."""

    instrument_symbol: str | None = None
    playbook_slug: str | None = None
    purpose: str | None = None
    direction: str | None = None
    horizon: str | None = None


class TradeThesisDraftPayload(BaseModel):
    """API payload for editable thesis draft data."""

    reasoning: str | None = None
    supporting_evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    disconfirming_signals: list[str] = Field(default_factory=list)


class TradePlanDraftPayload(BaseModel):
    """API payload for editable plan draft data."""

    entry_criteria: str | None = None
    invalidation: str | None = None
    targets: list[str] = Field(default_factory=list)
    risk_model: str | None = None
    sizing_assumptions: str | None = None


class TradeCaptureDraftPayload(BaseModel):
    """API payload for parsed or edited trade-capture draft data."""

    idea: TradeIdeaDraftPayload = Field(default_factory=TradeIdeaDraftPayload)
    thesis: TradeThesisDraftPayload = Field(default_factory=TradeThesisDraftPayload)
    plan: TradePlanDraftPayload = Field(default_factory=TradePlanDraftPayload)
    source_text: str | None = None
    ambiguous_field_issues: list[DraftFieldIssueResponse] = Field(default_factory=list)


class TradeCaptureParseRequest(BaseModel):
    """Request to parse raw trade-capture text."""

    source_text: str


class TradeCaptureDraftResponse(BaseModel):
    """Response containing an editable draft and readiness state."""

    draft: TradeCaptureDraftPayload
    validation_issues: list[DraftFieldIssueResponse]
    ready_to_save: bool


class SavedTradeCaptureResponse(BaseModel):
    """Response for a saved trade-capture result."""

    trade_idea_id: UUID
    trade_thesis_id: UUID
    trade_plan_id: UUID
    instrument_id: UUID
    playbook_id: UUID
    purpose: str
    direction: str
    horizon: str
    reasoning: str
    entry_criteria: str
    invalidation: str
    approval_state: str
    targets: list[str] = Field(default_factory=list)
    risk_model: str | None = None
    sizing_assumptions: str | None = None


class TradeIdeaResponse(BaseModel):
    """API representation of a persisted trade idea."""

    id: UUID
    instrument_id: UUID
    instrument_symbol: str | None = None
    instrument_name: str | None = None
    playbook_id: UUID
    playbook_slug: str | None = None
    playbook_name: str | None = None
    purpose: str
    direction: str
    horizon: str
    status: str
    created_at: datetime


class TradeThesisResponse(BaseModel):
    """API representation of a persisted trade thesis."""

    id: UUID
    trade_idea_id: UUID
    reasoning: str
    supporting_evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    disconfirming_signals: list[str] = Field(default_factory=list)


class TradePlanResponse(BaseModel):
    """API representation of a persisted trade plan."""

    id: UUID
    trade_idea_id: UUID
    trade_thesis_id: UUID
    entry_criteria: str
    invalidation: str
    targets: list[str] = Field(default_factory=list)
    risk_model: str | None = None
    sizing_assumptions: str | None = None
    approval_state: str
    created_at: datetime


class MarketContextSummaryResponse(BaseModel):
    """API metadata for a market context snapshot without full payload."""

    id: UUID
    instrument_id: UUID
    target_type: str | None = None
    target_id: UUID | None = None
    context_type: str
    source: str
    source_ref: str | None = None
    observed_at: datetime
    captured_at: datetime


class RuleEvaluationResponse(BaseModel):
    """API representation of a deterministic rule evaluation record."""

    id: UUID
    rule_id: UUID
    entity_type: str
    entity_id: UUID
    passed: bool
    details: str | None = None
    evaluated_at: datetime


class OrderIntentResponse(BaseModel):
    """API representation of an order intent linked to a plan."""

    id: UUID
    trade_plan_id: UUID
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    status: str
    created_at: datetime
    notes: str | None = None


class PositionResponse(BaseModel):
    """API representation of a position linked to a plan."""

    id: UUID
    trade_plan_id: UUID
    instrument_id: UUID
    purpose: str
    lifecycle_state: str
    opened_at: datetime
    closed_at: datetime | None = None
    current_quantity: Decimal
    average_entry_price: Decimal | None = None


class TradePlanSummaryResponse(BaseModel):
    """Compact trade plan list item with linked idea metadata."""

    id: UUID
    trade_idea_id: UUID
    trade_thesis_id: UUID
    instrument_id: UUID
    instrument_symbol: str | None = None
    playbook_id: UUID
    playbook_slug: str | None = None
    purpose: str
    direction: str
    horizon: str
    approval_state: str
    created_at: datetime
    linked_context_count: int


class TradePlanDetailResponse(BaseModel):
    """Plan detail response for browser inspection."""

    idea: TradeIdeaResponse
    thesis: TradeThesisResponse
    plan: TradePlanResponse
    rule_evaluations: list[RuleEvaluationResponse] = Field(default_factory=list)
    order_intents: list[OrderIntentResponse] = Field(default_factory=list)
    positions: list[PositionResponse] = Field(default_factory=list)
    market_context: list[MarketContextSummaryResponse] = Field(default_factory=list)


class CopyMarketContextRequest(BaseModel):
    """Request to copy an existing snapshot to a supported target."""

    target_type: str
    target_id: UUID


def create_app(
    *,
    repositories: JsonRepositorySet | None = None,
    reference_repository: ReferenceDataRepository | None = None,
    trade_capture_parser: TradeCaptureParser | None = None,
) -> FastAPI:
    """Create the local API application."""
    app = FastAPI(title="Trading System API", version="0.1.0")
    repositories = repositories or build_json_repositories(_json_store_path())
    reference_lookup = ReferenceLookupService(
        reference_repository or SeededReferenceDataRepository()
    )
    parser = trade_capture_parser

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/reference/instruments", response_model=list[InstrumentResponse])
    def list_instruments() -> list[InstrumentResponse]:
        return [
            _instrument_response(instrument)
            for instrument in reference_lookup.list_instruments()
        ]

    @app.get("/reference/instruments/{symbol}", response_model=InstrumentResponse)
    def get_instrument(symbol: str) -> InstrumentResponse:
        try:
            return _instrument_response(reference_lookup.resolve_instrument(symbol))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/reference/playbooks", response_model=list[PlaybookResponse])
    def list_playbooks() -> list[PlaybookResponse]:
        return [
            _playbook_response(playbook)
            for playbook in reference_lookup.list_playbooks()
        ]

    @app.get("/reference/playbooks/{slug}", response_model=PlaybookResponse)
    def get_playbook(slug: str) -> PlaybookResponse:
        try:
            return _playbook_response(reference_lookup.resolve_playbook(slug))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/trade-capture/parse", response_model=TradeCaptureDraftResponse)
    def parse_trade_capture(
        request: TradeCaptureParseRequest,
    ) -> TradeCaptureDraftResponse:
        service = _trade_capture_service(
            repositories=repositories,
            reference_lookup=reference_lookup,
            parser=_active_parser(parser),
        )
        try:
            draft = service.parse(request.source_text)
        except TradeCaptureParseError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _draft_response(draft)

    @app.post("/trade-capture/save", response_model=SavedTradeCaptureResponse)
    def save_trade_capture(
        draft_payload: TradeCaptureDraftPayload,
    ) -> SavedTradeCaptureResponse:
        service = _trade_capture_service(
            repositories=repositories,
            reference_lookup=reference_lookup,
            parser=parser or FakeTradeCaptureParser(),
        )
        try:
            saved = service.save_confirmed_draft(_draft_from_payload(draft_payload))
        except TradeCaptureValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": str(exc),
                    "issues": [
                        _issue_response(issue).model_dump() for issue in exc.issues
                    ],
                },
            ) from exc
        return _saved_response(saved)

    @app.get(
        "/trade-capture/saved/{trade_plan_id}",
        response_model=SavedTradeCaptureResponse,
    )
    def get_saved_trade_capture(trade_plan_id: UUID) -> SavedTradeCaptureResponse:
        service = _trade_capture_service(
            repositories=repositories,
            reference_lookup=reference_lookup,
            parser=parser or FakeTradeCaptureParser(),
        )
        try:
            return _saved_response(service.get_saved_result(trade_plan_id))
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/trade-plans", response_model=list[TradePlanSummaryResponse])
    def list_trade_plans(
        approval_state: str | None = None,
        sort: str = "newest",
    ) -> list[TradePlanSummaryResponse]:
        if sort not in {"oldest", "newest"}:
            raise HTTPException(status_code=422, detail="Sort must be oldest or newest.")
        queries = _trade_query_service(repositories)
        try:
            return [
                _plan_summary_response(
                    detail=queries.get_trade_plan_detail(plan.id),
                    reference_lookup=reference_lookup,
                )
                for plan in queries.list_trade_plans(
                    approval_state=approval_state,
                    sort=sort,  # type: ignore[arg-type]
                )
            ]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/trade-plans/{trade_plan_id}", response_model=TradePlanDetailResponse)
    def get_trade_plan(trade_plan_id: UUID) -> TradePlanDetailResponse:
        queries = _trade_query_service(repositories)
        try:
            return _plan_detail_response(
                queries.get_trade_plan_detail(trade_plan_id),
                reference_lookup=reference_lookup,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/trade-plans/{trade_plan_id}/approve",
        response_model=TradePlanDetailResponse,
    )
    def approve_trade_plan(trade_plan_id: UUID) -> TradePlanDetailResponse:
        planning = TradePlanningService(
            repositories.ideas,
            repositories.theses,
            repositories.plans,
        )
        queries = _trade_query_service(repositories)
        try:
            planning.approve_trade_plan(trade_plan_id)
            return _plan_detail_response(
                queries.get_trade_plan_detail(trade_plan_id),
                reference_lookup=reference_lookup,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/market-context", response_model=list[MarketContextSummaryResponse])
    def list_market_context(
        instrument_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        context_type: str | None = None,
        source: str | None = None,
    ) -> list[MarketContextSummaryResponse]:
        service = MarketContextQueryService(repositories.market_context_snapshots)
        try:
            return [
                _market_context_summary_response(snapshot)
                for snapshot in service.list_snapshots(
                    instrument_id=instrument_id,
                    target_type=target_type,
                    target_id=target_id,
                    context_type=context_type,
                    source=source,
                )
            ]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/market-context/{snapshot_id}/copy-to-target",
        response_model=MarketContextSummaryResponse,
    )
    def copy_market_context_to_target(
        snapshot_id: UUID,
        request: CopyMarketContextRequest,
    ) -> MarketContextSummaryResponse:
        if request.target_type != "TradePlan":
            raise HTTPException(
                status_code=422,
                detail="Milestone 9 supports browser attachment to TradePlan only.",
            )
        service = MarketContextImportService(
            snapshot_repository=repositories.market_context_snapshots,
            plan_repository=repositories.plans,
            position_repository=repositories.positions,
            review_repository=repositories.reviews,
            idea_repository=repositories.ideas,
        )
        try:
            return _market_context_summary_response(
                service.copy_context_to_target(
                    snapshot_id,
                    target_type=request.target_type,
                    target_id=request.target_id,
                )
            )
        except ValueError as exc:
            status_code = 404 if "does not exist" in str(exc) else 400
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return app


def _instrument_response(instrument: Instrument) -> InstrumentResponse:
    return InstrumentResponse(
        id=instrument.id,
        symbol=instrument.symbol,
        name=instrument.name,
    )


def _playbook_response(playbook: Playbook) -> PlaybookResponse:
    return PlaybookResponse(
        id=playbook.id,
        slug=playbook.slug,
        name=playbook.name,
        description=playbook.description,
    )


def _trade_capture_service(
    *,
    repositories: JsonRepositorySet,
    reference_lookup: ReferenceLookupService,
    parser: TradeCaptureParser,
) -> TradeCaptureService:
    planning = TradePlanningService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
    )
    queries = TradeQueryService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
        repositories.evaluations,
        repositories.order_intents,
        repositories.positions,
        repositories.market_context_snapshots,
    )
    return TradeCaptureService(
        parser=parser,
        reference_lookup=reference_lookup,
        planning=planning,
        queries=queries,
    )


def _trade_query_service(repositories: JsonRepositorySet) -> TradeQueryService:
    return TradeQueryService(
        repositories.ideas,
        repositories.theses,
        repositories.plans,
        repositories.evaluations,
        repositories.order_intents,
        repositories.positions,
        repositories.market_context_snapshots,
    )


def _active_parser(parser: TradeCaptureParser | None) -> TradeCaptureParser:
    if parser is not None:
        return parser
    return LiteLLMTradeCaptureParser(LiteLLMTradeCaptureParserConfig.from_env())


def _draft_response(draft: TradeCaptureDraft) -> TradeCaptureDraftResponse:
    return TradeCaptureDraftResponse(
        draft=_draft_payload(draft),
        validation_issues=[
            _issue_response(issue) for issue in draft.validation_issues()
        ],
        ready_to_save=draft.is_ready_to_save(),
    )


def _draft_payload(draft: TradeCaptureDraft) -> TradeCaptureDraftPayload:
    return TradeCaptureDraftPayload(
        idea=TradeIdeaDraftPayload(
            instrument_symbol=draft.idea.instrument_symbol,
            playbook_slug=draft.idea.playbook_slug,
            purpose=draft.idea.purpose,
            direction=draft.idea.direction,
            horizon=draft.idea.horizon,
        ),
        thesis=TradeThesisDraftPayload(
            reasoning=draft.thesis.reasoning,
            supporting_evidence=list(draft.thesis.supporting_evidence),
            risks=list(draft.thesis.risks),
            disconfirming_signals=list(draft.thesis.disconfirming_signals),
        ),
        plan=TradePlanDraftPayload(
            entry_criteria=draft.plan.entry_criteria,
            invalidation=draft.plan.invalidation,
            targets=list(draft.plan.targets),
            risk_model=draft.plan.risk_model,
            sizing_assumptions=draft.plan.sizing_assumptions,
        ),
        source_text=draft.source_text,
        ambiguous_field_issues=[
            _issue_response(issue) for issue in draft.ambiguous_field_issues
        ],
    )


def _draft_from_payload(payload: TradeCaptureDraftPayload) -> TradeCaptureDraft:
    return TradeCaptureDraft(
        idea=TradeIdeaDraft(
            instrument_symbol=payload.idea.instrument_symbol,
            playbook_slug=payload.idea.playbook_slug,
            purpose=payload.idea.purpose,
            direction=payload.idea.direction,
            horizon=payload.idea.horizon,
        ),
        thesis=TradeThesisDraft(
            reasoning=payload.thesis.reasoning,
            supporting_evidence=list(payload.thesis.supporting_evidence),
            risks=list(payload.thesis.risks),
            disconfirming_signals=list(payload.thesis.disconfirming_signals),
        ),
        plan=TradePlanDraft(
            entry_criteria=payload.plan.entry_criteria,
            invalidation=payload.plan.invalidation,
            targets=list(payload.plan.targets),
            risk_model=payload.plan.risk_model,
            sizing_assumptions=payload.plan.sizing_assumptions,
        ),
        source_text=payload.source_text,
        ambiguous_field_issues=[
            DraftFieldIssue(
                entity=issue.entity,  # type: ignore[arg-type]
                field=issue.field,
                issue_type="ambiguous",
                message=issue.message,
                candidates=tuple(issue.candidates),
            )
            for issue in payload.ambiguous_field_issues
        ],
    )


def _issue_response(issue: DraftFieldIssue) -> DraftFieldIssueResponse:
    return DraftFieldIssueResponse(
        entity=issue.entity,
        field=issue.field,
        path=issue.path,
        issue_type=issue.issue_type,
        message=issue.message,
        candidates=list(issue.candidates),
    )


def _saved_response(saved: SavedTradeCapture) -> SavedTradeCaptureResponse:
    return SavedTradeCaptureResponse(
        trade_idea_id=saved.trade_idea.id,
        trade_thesis_id=saved.trade_thesis.id,
        trade_plan_id=saved.trade_plan.id,
        instrument_id=saved.trade_idea.instrument_id,
        playbook_id=saved.trade_idea.playbook_id,
        purpose=saved.trade_idea.purpose,
        direction=saved.trade_idea.direction,
        horizon=saved.trade_idea.horizon,
        reasoning=saved.trade_thesis.reasoning,
        entry_criteria=saved.trade_plan.entry_criteria,
        invalidation=saved.trade_plan.invalidation,
        approval_state=saved.trade_plan.approval_state,
        targets=list(saved.trade_plan.targets),
        risk_model=saved.trade_plan.risk_model,
        sizing_assumptions=saved.trade_plan.sizing_assumptions,
    )


def _plan_summary_response(
    *,
    detail: TradePlanDetail,
    reference_lookup: ReferenceLookupService,
) -> TradePlanSummaryResponse:
    instrument = _find_instrument(reference_lookup, detail.trade_idea.instrument_id)
    playbook = _find_playbook(reference_lookup, detail.trade_idea.playbook_id)
    return TradePlanSummaryResponse(
        id=detail.trade_plan.id,
        trade_idea_id=detail.trade_plan.trade_idea_id,
        trade_thesis_id=detail.trade_plan.trade_thesis_id,
        instrument_id=detail.trade_idea.instrument_id,
        instrument_symbol=instrument.symbol if instrument else None,
        playbook_id=detail.trade_idea.playbook_id,
        playbook_slug=playbook.slug if playbook else None,
        purpose=detail.trade_idea.purpose,
        direction=detail.trade_idea.direction,
        horizon=detail.trade_idea.horizon,
        approval_state=detail.trade_plan.approval_state,
        created_at=detail.trade_plan.created_at,
        linked_context_count=len(detail.market_context_snapshots),
    )


def _plan_detail_response(
    detail: TradePlanDetail,
    *,
    reference_lookup: ReferenceLookupService,
) -> TradePlanDetailResponse:
    instrument = _find_instrument(reference_lookup, detail.trade_idea.instrument_id)
    playbook = _find_playbook(reference_lookup, detail.trade_idea.playbook_id)
    return TradePlanDetailResponse(
        idea=TradeIdeaResponse(
            id=detail.trade_idea.id,
            instrument_id=detail.trade_idea.instrument_id,
            instrument_symbol=instrument.symbol if instrument else None,
            instrument_name=instrument.name if instrument else None,
            playbook_id=detail.trade_idea.playbook_id,
            playbook_slug=playbook.slug if playbook else None,
            playbook_name=playbook.name if playbook else None,
            purpose=detail.trade_idea.purpose,
            direction=detail.trade_idea.direction,
            horizon=detail.trade_idea.horizon,
            status=detail.trade_idea.status,
            created_at=detail.trade_idea.created_at,
        ),
        thesis=TradeThesisResponse(
            id=detail.trade_thesis.id,
            trade_idea_id=detail.trade_thesis.trade_idea_id,
            reasoning=detail.trade_thesis.reasoning,
            supporting_evidence=list(detail.trade_thesis.supporting_evidence),
            risks=list(detail.trade_thesis.risks),
            disconfirming_signals=list(detail.trade_thesis.disconfirming_signals),
        ),
        plan=TradePlanResponse(
            id=detail.trade_plan.id,
            trade_idea_id=detail.trade_plan.trade_idea_id,
            trade_thesis_id=detail.trade_plan.trade_thesis_id,
            entry_criteria=detail.trade_plan.entry_criteria,
            invalidation=detail.trade_plan.invalidation,
            targets=list(detail.trade_plan.targets),
            risk_model=detail.trade_plan.risk_model,
            sizing_assumptions=detail.trade_plan.sizing_assumptions,
            approval_state=detail.trade_plan.approval_state,
            created_at=detail.trade_plan.created_at,
        ),
        rule_evaluations=[
            RuleEvaluationResponse(
                id=evaluation.id,
                rule_id=evaluation.rule_id,
                entity_type=evaluation.entity_type,
                entity_id=evaluation.entity_id,
                passed=evaluation.passed,
                details=evaluation.details,
                evaluated_at=evaluation.evaluated_at,
            )
            for evaluation in detail.rule_evaluations
        ],
        order_intents=[
            _order_intent_response(order_intent)
            for order_intent in detail.order_intents
        ],
        positions=[_position_response(position) for position in detail.positions],
        market_context=[
            _market_context_summary_response(snapshot)
            for snapshot in detail.market_context_snapshots
        ],
    )


def _market_context_summary_response(
    snapshot: MarketContextSnapshot,
) -> MarketContextSummaryResponse:
    return MarketContextSummaryResponse(
        id=snapshot.id,
        instrument_id=snapshot.instrument_id,
        target_type=snapshot.target_type,
        target_id=snapshot.target_id,
        context_type=snapshot.context_type,
        source=snapshot.source,
        source_ref=snapshot.source_ref,
        observed_at=snapshot.observed_at,
        captured_at=snapshot.captured_at,
    )


def _order_intent_response(order_intent: OrderIntent) -> OrderIntentResponse:
    return OrderIntentResponse(
        id=order_intent.id,
        trade_plan_id=order_intent.trade_plan_id,
        symbol=order_intent.symbol,
        side=order_intent.side.value,
        order_type=order_intent.order_type.value,
        quantity=order_intent.quantity,
        limit_price=order_intent.limit_price,
        stop_price=order_intent.stop_price,
        status=order_intent.status.value,
        created_at=order_intent.created_at,
        notes=order_intent.notes,
    )


def _position_response(position: Position) -> PositionResponse:
    return PositionResponse(
        id=position.id,
        trade_plan_id=position.trade_plan_id,
        instrument_id=position.instrument_id,
        purpose=position.purpose,
        lifecycle_state=position.lifecycle_state,
        opened_at=position.opened_at,
        closed_at=position.closed_at,
        current_quantity=position.current_quantity,
        average_entry_price=position.average_entry_price,
    )


def _find_instrument(
    reference_lookup: ReferenceLookupService,
    instrument_id: UUID,
) -> Instrument | None:
    for instrument in reference_lookup.list_instruments():
        if instrument.id == instrument_id:
            return instrument
    return None


def _find_playbook(
    reference_lookup: ReferenceLookupService,
    playbook_id: UUID,
) -> Playbook | None:
    for playbook in reference_lookup.list_playbooks():
        if playbook.id == playbook_id:
            return playbook
    return None


def _json_store_path() -> Path:
    configured = os.environ.get("TRADING_SYSTEM_STORE_PATH")
    if configured:
        return Path(configured)
    return Path(".trading-system") / "store.json"


app = create_app()
