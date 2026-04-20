"""SQLAlchemy models for trading entities."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from trading_system.infrastructure.db.base import Base


class InstrumentModel(Base):
    """Persisted instrument identity."""

    __tablename__ = "instruments"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255))


class TradeIdeaModel(Base):
    """Persisted trade idea."""

    __tablename__ = "trade_ideas"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"))
    playbook_id: Mapped[UUID] = mapped_column(nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class TradeThesisModel(Base):
    """Persisted trade thesis."""

    __tablename__ = "trade_theses"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trade_idea_id: Mapped[UUID] = mapped_column(ForeignKey("trade_ideas.id"))
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    risks: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    disconfirming_signals: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class TradePlanModel(Base):
    """Persisted trade plan."""

    __tablename__ = "trade_plans"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trade_idea_id: Mapped[UUID] = mapped_column(ForeignKey("trade_ideas.id"))
    trade_thesis_id: Mapped[UUID] = mapped_column(ForeignKey("trade_theses.id"))
    entry_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation: Mapped[str] = mapped_column(Text, nullable=False)
    targets: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    risk_model: Mapped[str | None] = mapped_column(Text)
    sizing_assumptions: Mapped[str | None] = mapped_column(Text)
    approval_state: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PositionModel(Base):
    """Persisted position derived from a trade plan."""

    __tablename__ = "positions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trade_plan_id: Mapped[UUID] = mapped_column(ForeignKey("trade_plans.id"))
    instrument_id: Mapped[UUID] = mapped_column(ForeignKey("instruments.id"))
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_bought_quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    total_sold_quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    current_quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    average_entry_price: Mapped[Decimal | None] = mapped_column(Numeric)


class FillModel(Base):
    """Persisted manual fill fact."""

    __tablename__ = "fills"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), nullable=False)


class TradeReviewModel(Base):
    """Persisted trade review."""

    __tablename__ = "trade_reviews"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.id"))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    lessons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LifecycleEventModel(Base):
    """Persisted lifecycle event."""

    __tablename__ = "lifecycle_events"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
