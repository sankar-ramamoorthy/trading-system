"""Shared trade-capture parser errors and test helpers."""

from trading_system.services.trade_capture_draft import TradeCaptureDraft


class TradeCaptureParseError(ValueError):
    """Raised when source text cannot be parsed into a trade-capture draft."""


class FakeTradeCaptureParser:
    """Deterministic parser for tests and non-LLM wiring."""

    def __init__(self, draft: TradeCaptureDraft | None = None) -> None:
        self._draft = draft or TradeCaptureDraft()

    def parse(self, source_text: str) -> TradeCaptureDraft:
        """Return the configured draft with the caller's source text attached."""
        if not source_text.strip():
            raise TradeCaptureParseError("Trade capture text is required.")
        self._draft.source_text = source_text
        return self._draft
