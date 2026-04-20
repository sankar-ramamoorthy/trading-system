"""Position entity representing the system's interpretation of a holding."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from trading_system.domain.trading.fill import Fill


@dataclass
class Position:
    """A holding that originates from a trade plan, not directly from an idea."""

    trade_plan_id: UUID
    instrument_id: UUID
    purpose: str
    lifecycle_state: str = "open"
    opened_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None
    total_bought_quantity: Decimal = Decimal("0")
    total_sold_quantity: Decimal = Decimal("0")
    current_quantity: Decimal = Decimal("0")
    average_entry_price: Decimal | None = None
    closing_fill_id: UUID | None = None
    close_reason: str | None = None
    id: UUID = field(default_factory=uuid4)

    def record_fill(self, fill: Fill) -> None:
        """Apply a manual fill to this position and update execution state."""
        if self.lifecycle_state != "open":
            raise ValueError("Cannot record a fill on a closed position.")
        if fill.position_id != self.id:
            raise ValueError("Fill does not belong to this position.")
        if fill.quantity <= 0:
            raise ValueError("Fill quantity must be positive.")
        if fill.price <= 0:
            raise ValueError("Fill price must be positive.")

        side = fill.side.lower()
        if side == "buy":
            self._record_buy(fill)
            return
        if side == "sell":
            self._record_sell(fill)
            return
        raise ValueError("Fill side must be 'buy' or 'sell'.")

    def _record_buy(self, fill: Fill) -> None:
        """Increase long exposure and recompute weighted average entry."""
        existing_cost = self.current_quantity * (self.average_entry_price or Decimal("0"))
        fill_cost = fill.quantity * fill.price
        new_quantity = self.current_quantity + fill.quantity

        self.total_bought_quantity += fill.quantity
        self.current_quantity = new_quantity
        self.average_entry_price = (existing_cost + fill_cost) / new_quantity

    def _record_sell(self, fill: Fill) -> None:
        """Reduce long exposure without allowing reversal."""
        if fill.quantity > self.current_quantity:
            raise ValueError("Reducing fill cannot exceed current open quantity.")

        self.total_sold_quantity += fill.quantity
        self.current_quantity -= fill.quantity
        if self.current_quantity == 0:
            self.average_entry_price = None
            self.lifecycle_state = "closed"
            self.closed_at = fill.filled_at
            self.closing_fill_id = fill.id
            self.close_reason = "fills_completed"
