"""FastAPI entrypoint for local web workflows."""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from trading_system.domain.trading.instrument import Instrument
from trading_system.domain.trading.playbook import Playbook
from trading_system.infrastructure.seeded_reference_data import (
    SeededReferenceDataRepository,
)
from trading_system.services.reference_lookup_service import ReferenceLookupService


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


def create_app() -> FastAPI:
    """Create the local API application."""
    app = FastAPI(title="Trading System API", version="0.1.0")
    reference_lookup = ReferenceLookupService(SeededReferenceDataRepository())

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=False,
        allow_methods=["GET"],
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

    return app


app = create_app()


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
