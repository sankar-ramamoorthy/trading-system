"""Repository implementation placeholders for trading entities."""

from sqlalchemy.orm import Session


class SqlAlchemyTradeIdeaRepository:
    """SQLAlchemy-backed trade idea repository skeleton."""

    def __init__(self, session: Session) -> None:
        self.session = session


class SqlAlchemyTradePlanRepository:
    """SQLAlchemy-backed trade plan repository skeleton."""

    def __init__(self, session: Session) -> None:
        self.session = session


class SqlAlchemyPositionRepository:
    """SQLAlchemy-backed position repository skeleton."""

    def __init__(self, session: Session) -> None:
        self.session = session
