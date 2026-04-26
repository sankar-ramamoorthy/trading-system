"""Use cases for importing and inspecting read-only market context."""

from datetime import datetime
from uuid import UUID

from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.ports.market_context import MarketContextImportSource
from trading_system.ports.repositories import (
    MarketContextSnapshotRepository,
    PositionRepository,
    TradeIdeaRepository,
    TradePlanRepository,
    TradeReviewRepository,
)


VALID_CONTEXT_TARGET_TYPES = {"TradePlan", "Position", "TradeReview"}


class MarketContextImportService:
    """Coordinates explicit market context imports without interpreting them."""

    def __init__(
        self,
        snapshot_repository: MarketContextSnapshotRepository,
        plan_repository: TradePlanRepository,
        position_repository: PositionRepository,
        review_repository: TradeReviewRepository,
        idea_repository: TradeIdeaRepository,
    ) -> None:
        self._snapshots = snapshot_repository
        self._plans = plan_repository
        self._positions = position_repository
        self._reviews = review_repository
        self._ideas = idea_repository

    def import_context(
        self,
        source_adapter: MarketContextImportSource,
        *,
        source: str,
        source_ref: str | None = None,
        instrument_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
    ) -> MarketContextSnapshot:
        """Import one read-only context snapshot."""
        if (target_type is None) != (target_id is None):
            raise ValueError("Target type and target id must be provided together.")
        if target_type is not None and target_type not in VALID_CONTEXT_TARGET_TYPES:
            raise ValueError("Context target type is not supported.")

        resolved_instrument_id = self._resolve_instrument_id(
            instrument_id=instrument_id,
            target_type=target_type,
            target_id=target_id,
        )
        imported = source_adapter.load()
        snapshot = MarketContextSnapshot(
            instrument_id=resolved_instrument_id,
            target_type=target_type,
            target_id=target_id,
            context_type=imported.context_type,
            source=source,
            source_ref=source_ref,
            observed_at=imported.observed_at,
            payload=imported.payload,
        )
        self._snapshots.add(snapshot)
        return snapshot

    def copy_context_to_target(
        self,
        snapshot_id: UUID,
        *,
        target_type: str,
        target_id: UUID,
    ) -> MarketContextSnapshot:
        """Copy an existing snapshot to a new planning or review target."""
        if target_type not in VALID_CONTEXT_TARGET_TYPES:
            raise ValueError("Context target type is not supported.")

        original = self._snapshots.get(snapshot_id)
        if original is None:
            raise ValueError("Market context snapshot does not exist.")

        resolved_instrument_id = self._resolve_instrument_id(
            instrument_id=original.instrument_id,
            target_type=target_type,
            target_id=target_id,
        )
        snapshot = MarketContextSnapshot(
            instrument_id=resolved_instrument_id,
            target_type=target_type,
            target_id=target_id,
            context_type=original.context_type,
            source=original.source,
            source_ref=original.source_ref,
            observed_at=original.observed_at,
            payload=dict(original.payload),
        )
        self._snapshots.add(snapshot)
        return snapshot

    def _resolve_instrument_id(
        self,
        *,
        instrument_id: UUID | None,
        target_type: str | None,
        target_id: UUID | None,
    ) -> UUID:
        if target_type is None:
            if instrument_id is None:
                raise ValueError("Instrument id is required when no context target is provided.")
            return instrument_id

        if target_type == "TradePlan":
            plan = self._plans.get(target_id)
            if plan is None:
                raise ValueError("Trade plan does not exist for context target.")
            idea = self._ideas.get(plan.trade_idea_id)
            if idea is None:
                raise ValueError("Trade idea does not exist for context target.")
            return _validate_or_use_instrument_id(instrument_id, idea.instrument_id)

        if target_type == "Position":
            position = self._positions.get(target_id)
            if position is None:
                raise ValueError("Position does not exist for context target.")
            return _validate_or_use_instrument_id(instrument_id, position.instrument_id)

        review = self._reviews.get(target_id)
        if review is None:
            raise ValueError("Trade review does not exist for context target.")
        position = self._positions.get(review.position_id)
        if position is None:
            raise ValueError("Position does not exist for context target.")
        return _validate_or_use_instrument_id(instrument_id, position.instrument_id)


class MarketContextQueryService:
    """Coordinates read-only market context retrieval."""

    def __init__(
        self,
        snapshot_repository: MarketContextSnapshotRepository,
    ) -> None:
        self._snapshots = snapshot_repository

    def get_snapshot(self, snapshot_id: UUID) -> MarketContextSnapshot:
        """Return one stored market context snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            raise ValueError("Market context snapshot does not exist.")
        return snapshot

    def list_by_instrument_id(self, instrument_id: UUID) -> list[MarketContextSnapshot]:
        """Return context snapshots for one instrument."""
        return self._snapshots.list_by_instrument_id(instrument_id)

    def list_by_target(
        self,
        target_type: str,
        target_id: UUID,
    ) -> list[MarketContextSnapshot]:
        """Return context snapshots linked to one target."""
        if target_type not in VALID_CONTEXT_TARGET_TYPES:
            raise ValueError("Context target type is not supported.")
        return self._snapshots.list_by_target(target_type, target_id)

    def list_snapshots(
        self,
        *,
        instrument_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        context_type: str | None = None,
        source: str | None = None,
        observed_from: datetime | None = None,
        observed_to: datetime | None = None,
        captured_from: datetime | None = None,
        captured_to: datetime | None = None,
    ) -> list[MarketContextSnapshot]:
        """Return context snapshots matching optional discovery filters."""
        if (target_type is None) != (target_id is None):
            raise ValueError("Target type and target id must be provided together.")
        if target_type is not None and target_type not in VALID_CONTEXT_TARGET_TYPES:
            raise ValueError("Context target type is not supported.")

        snapshots = self._snapshots.list_all()
        if instrument_id is not None:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.instrument_id == instrument_id
            ]
        if target_type is not None:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.target_type == target_type and snapshot.target_id == target_id
            ]
        if context_type is not None:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.context_type == context_type
            ]
        if source is not None:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.source == source
            ]
        if observed_from is not None:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.observed_at >= observed_from
            ]
        if observed_to is not None:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.observed_at <= observed_to
            ]
        if captured_from is not None:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.captured_at >= captured_from
            ]
        if captured_to is not None:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot.captured_at <= captured_to
            ]
        return sorted(snapshots, key=lambda snapshot: snapshot.captured_at)


def _validate_or_use_instrument_id(
    provided: UUID | None,
    resolved: UUID,
) -> UUID:
    if provided is not None and provided != resolved:
        raise ValueError("Instrument id does not match the context target.")
    return resolved
