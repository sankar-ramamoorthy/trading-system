"""Trade thesis entity defining why a trade exists."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class TradeThesis:
    """Reasoning, evidence, risks, and invalidating signals for an idea."""

    trade_idea_id: UUID
    reasoning: str
    supporting_evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    disconfirming_signals: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
