"""FastAPI entrypoint for local web workflows."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from trading_system.domain.trading.instrument import Instrument
from trading_system.domain.trading.playbook import Playbook
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
from trading_system.services.trade_query_service import TradeQueryService


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


def _json_store_path() -> Path:
    configured = os.environ.get("TRADING_SYSTEM_STORE_PATH")
    if configured:
        return Path(configured)
    return Path(".trading-system") / "store.json"


app = create_app()
