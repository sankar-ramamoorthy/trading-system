"""Editable trade-capture draft contracts for parser and API workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DraftEntityName = Literal["TradeIdea", "TradeThesis", "TradePlan"]
DraftIssueType = Literal["missing", "ambiguous"]


@dataclass(frozen=True)
class DraftFieldDefinition:
    """Save-field contract for one editable trade-capture draft field."""

    entity: DraftEntityName
    field: str
    required: bool
    description: str

    @property
    def path(self) -> str:
        """Return a stable path for API/UI field reporting."""
        return f"{self.entity}.{self.field}"


@dataclass(frozen=True)
class DraftFieldIssue:
    """Missing or ambiguous draft field that must be surfaced to the user."""

    entity: DraftEntityName
    field: str
    issue_type: DraftIssueType
    message: str
    candidates: tuple[str, ...] = ()

    @property
    def path(self) -> str:
        """Return a stable path for API/UI field reporting."""
        return f"{self.entity}.{self.field}"


@dataclass
class TradeIdeaDraft:
    """Editable draft for what the trade is."""

    instrument_symbol: str | None = None
    playbook_slug: str | None = None
    purpose: str | None = None
    direction: str | None = None
    horizon: str | None = None


@dataclass
class TradeThesisDraft:
    """Editable draft for why the trade exists."""

    reasoning: str | None = None
    supporting_evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    disconfirming_signals: list[str] = field(default_factory=list)


@dataclass
class TradePlanDraft:
    """Editable draft for how the trade would be executed."""

    entry_criteria: str | None = None
    invalidation: str | None = None
    targets: list[str] = field(default_factory=list)
    risk_model: str | None = None
    sizing_assumptions: str | None = None


@dataclass
class TradeCaptureDraft:
    """Parsed, editable trade-capture draft that has not been persisted."""

    idea: TradeIdeaDraft = field(default_factory=TradeIdeaDraft)
    thesis: TradeThesisDraft = field(default_factory=TradeThesisDraft)
    plan: TradePlanDraft = field(default_factory=TradePlanDraft)
    source_text: str | None = None
    ambiguous_field_issues: list[DraftFieldIssue] = field(default_factory=list)

    def validation_issues(self) -> list[DraftFieldIssue]:
        """Return missing and ambiguous fields blocking a clean save."""
        return [*self.missing_required_issues(), *self.ambiguous_issues()]

    def missing_required_issues(self) -> list[DraftFieldIssue]:
        """Return required save fields that are absent or blank."""
        issues: list[DraftFieldIssue] = []
        for definition in required_draft_fields():
            value = self._field_value(definition)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(
                    DraftFieldIssue(
                        entity=definition.entity,
                        field=definition.field,
                        issue_type="missing",
                        message=f"{definition.path} is required before save.",
                    )
                )
        return issues

    def ambiguous_issues(self) -> list[DraftFieldIssue]:
        """Return parser-reported ambiguous fields."""
        return list(self.ambiguous_field_issues)

    def is_ready_to_save(self) -> bool:
        """Return whether the draft has all required fields and no ambiguity."""
        return not self.validation_issues()

    def _field_value(self, definition: DraftFieldDefinition) -> object:
        section = {
            "TradeIdea": self.idea,
            "TradeThesis": self.thesis,
            "TradePlan": self.plan,
        }[definition.entity]
        return getattr(section, definition.field)


DRAFT_FIELD_DEFINITIONS: tuple[DraftFieldDefinition, ...] = (
    DraftFieldDefinition(
        "TradeIdea",
        "instrument_symbol",
        True,
        "User-facing instrument symbol resolved later through reference lookup.",
    ),
    DraftFieldDefinition(
        "TradeIdea",
        "playbook_slug",
        True,
        "User-facing playbook slug resolved later through reference lookup.",
    ),
    DraftFieldDefinition("TradeIdea", "purpose", True, "Trade purpose."),
    DraftFieldDefinition("TradeIdea", "direction", True, "Trade direction."),
    DraftFieldDefinition("TradeIdea", "horizon", True, "Expected trade horizon."),
    DraftFieldDefinition("TradeThesis", "reasoning", True, "Core trade thesis."),
    DraftFieldDefinition(
        "TradeThesis",
        "supporting_evidence",
        False,
        "User-authored supporting observations.",
    ),
    DraftFieldDefinition(
        "TradeThesis",
        "risks",
        False,
        "User-authored thesis risks.",
    ),
    DraftFieldDefinition(
        "TradeThesis",
        "disconfirming_signals",
        False,
        "User-authored thesis invalidation evidence.",
    ),
    DraftFieldDefinition(
        "TradePlan",
        "entry_criteria",
        True,
        "User-authored criteria for entering the trade.",
    ),
    DraftFieldDefinition(
        "TradePlan",
        "invalidation",
        True,
        "User-authored plan invalidation condition.",
    ),
    DraftFieldDefinition("TradePlan", "targets", False, "User-authored targets."),
    DraftFieldDefinition(
        "TradePlan",
        "risk_model",
        False,
        "User-authored risk model.",
    ),
    DraftFieldDefinition(
        "TradePlan",
        "sizing_assumptions",
        False,
        "User-authored sizing assumptions.",
    ),
)


def required_draft_fields() -> tuple[DraftFieldDefinition, ...]:
    """Return fields required to save a captured draft."""
    return tuple(
        definition
        for definition in DRAFT_FIELD_DEFINITIONS
        if definition.required
    )


def optional_draft_fields() -> tuple[DraftFieldDefinition, ...]:
    """Return optional editable draft fields."""
    return tuple(
        definition
        for definition in DRAFT_FIELD_DEFINITIONS
        if not definition.required
    )
