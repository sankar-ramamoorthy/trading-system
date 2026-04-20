"""Demonstrate the scaffolded swing-trade object chain without persistence."""

from uuid import uuid4

from trading_system.domain.rules.rule import Rule
from trading_system.domain.trading.idea import TradeIdea
from trading_system.domain.trading.instrument import Instrument
from trading_system.domain.trading.plan import TradePlan
from trading_system.domain.trading.position import Position
from trading_system.domain.trading.review import TradeReview
from trading_system.domain.trading.thesis import TradeThesis
from trading_system.rules_engine.implementations.risk_defined_rule import RiskDefinedRule


def main() -> None:
    """Create the initial vertical-slice objects in memory."""
    instrument = Instrument(symbol="AAPL", name="Apple Inc.")
    idea = TradeIdea(
        instrument_id=instrument.id,
        playbook_id=uuid4(),
        purpose="Example swing trade setup.",
        direction="long",
        horizon="swing",
    )
    thesis = TradeThesis(
        trade_idea_id=idea.id,
        reasoning="Example thesis placeholder.",
        supporting_evidence=["Price action placeholder."],
        risks=["Risk placeholder."],
    )
    plan = TradePlan(
        trade_idea_id=idea.id,
        trade_thesis_id=thesis.id,
        entry_criteria="Example entry criteria.",
        invalidation="Example invalidation.",
        targets=["Example target."],
        risk_model="Example defined risk.",
    )
    position = Position(
        trade_plan_id=plan.id,
        instrument_id=instrument.id,
        purpose=idea.purpose,
    )
    risk_rule = Rule(
        code="risk_defined",
        name="Risk defined",
        description="Trade plans must define risk before execution.",
    )
    passed, violations = RiskDefinedRule(risk_rule).evaluate(plan)
    review = TradeReview(
        position_id=position.id,
        summary="Example review placeholder.",
        what_went_well="Example strength.",
        what_went_poorly="Example weakness.",
        lessons_learned=["Example lesson."],
    )

    print(
        "Created scaffold demo: "
        f"{idea.id} -> {thesis.id} -> {plan.id} -> {position.id} -> "
        f"rule passed={passed} with {len(violations)} violations -> {review.id}"
    )


if __name__ == "__main__":
    main()
