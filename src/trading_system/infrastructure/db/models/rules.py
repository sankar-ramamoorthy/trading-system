"""SQLAlchemy models for rules, evaluations, and violations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from trading_system.infrastructure.db.base import Base


class RuleModel(Base):
    """Persisted deterministic rule definition."""

    __tablename__ = "rules"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class RuleEvaluationModel(Base):
    """Persisted rule evaluation result."""

    __tablename__ = "rule_evaluations"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("rules.id"))
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ViolationModel(Base):
    """Persisted rule violation."""

    __tablename__ = "violations"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("rules.id"))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
