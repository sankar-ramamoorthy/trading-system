"""Parser ports for natural-language trade capture."""

from typing import Protocol

from trading_system.services.trade_capture_draft import TradeCaptureDraft


class TradeCaptureParser(Protocol):
    """Parse user-authored trade language into an editable draft."""

    def parse(self, source_text: str) -> TradeCaptureDraft:
        """Return an unsaved trade-capture draft."""
        ...
