"""Repository implementation placeholders for rule entities."""

from sqlalchemy.orm import Session


class SqlAlchemyRuleEvaluationRepository:
    """SQLAlchemy-backed rule evaluation repository skeleton."""

    def __init__(self, session: Session) -> None:
        self.session = session
