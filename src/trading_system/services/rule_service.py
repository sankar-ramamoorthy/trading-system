"""Service stubs for deterministic rule evaluation workflows."""

from trading_system.domain.rules.rule_evaluation import RuleEvaluation


class RuleService:
    """Coordinates rule evaluation workflows without persistence details."""

    def evaluate_rules_for_entity(
        self,
        entity_type: str,
        entity_id: object,
    ) -> list[RuleEvaluation]:
        """Evaluate deterministic rules for a scoped domain entity."""
        raise NotImplementedError("Rule evaluation workflow is not implemented yet.")
