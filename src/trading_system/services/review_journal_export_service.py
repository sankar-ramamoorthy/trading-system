"""Markdown journal export for reviewed trades."""

from decimal import Decimal
from typing import Literal

from trading_system.domain.trading.market_context import MarketContextSnapshot
from trading_system.services.review_query_service import (
    ReviewQueryService,
    TradeReviewDetail,
)


class ReviewJournalExportService:
    """Build journal-grade Markdown from persisted trade reviews."""

    def __init__(self, review_query_service: ReviewQueryService) -> None:
        self._reviews = review_query_service

    def export_markdown(
        self,
        *,
        rating: int | None = None,
        purpose: str | None = None,
        direction: str | None = None,
        tags: list[str] | None = None,
        process_score: int | None = None,
        setup_quality: int | None = None,
        execution_quality: int | None = None,
        exit_quality: int | None = None,
        sort: Literal["oldest", "newest"] = "oldest",
    ) -> str | None:
        """Return Markdown for matching reviews, or None when no reviews match."""
        items = self._reviews.list_trade_reviews(
            rating=rating,
            purpose=purpose,
            direction=direction,
            tags=tags,
            process_score=process_score,
            setup_quality=setup_quality,
            execution_quality=execution_quality,
            exit_quality=exit_quality,
            sort=sort,
        )
        if not items:
            return None

        details = [
            self._reviews.get_trade_review_detail(item.review.id)
            for item in items
        ]
        return _render_markdown(details)


def _render_markdown(details: list[TradeReviewDetail]) -> str:
    lines = [
        "# Trade Review Journal",
        "",
    ]
    for index, detail in enumerate(details, start=1):
        review = detail.review
        lines.extend(
            [
                f"## Review {index}: {review.id}",
                "",
                "- Review id: " + str(review.id),
                "- Reviewed at: " + review.reviewed_at.isoformat(),
                "- Position id: " + str(detail.position.id),
                "- Trade plan id: " + str(detail.trade_plan.id),
                "- Purpose: " + detail.trade_idea.purpose,
                "- Direction: " + detail.trade_idea.direction,
                "- Realized P&L: " + _format_optional_decimal(detail.realized_pnl),
                "- Rating: " + _format_optional_value(review.rating),
                "- Tags: " + (", ".join(review.tags) if review.tags else "None"),
                "- Process score: " + _format_optional_value(review.process_score),
                "- Setup quality: " + _format_optional_value(review.setup_quality),
                "- Execution quality: " + _format_optional_value(review.execution_quality),
                "- Exit quality: " + _format_optional_value(review.exit_quality),
                "",
                "### Review Notes",
                "",
                "- Summary: " + review.summary,
                "- What went well: " + review.what_went_well,
                "- What went poorly: " + review.what_went_poorly,
                "",
                "### Lessons Learned",
                "",
            ]
        )
        lines.extend(_render_bullets(review.lessons_learned))
        lines.extend(["", "### Follow-up Actions", ""])
        lines.extend(_render_bullets(review.follow_up_actions))
        lines.extend(["", "### Market Context", ""])
        lines.extend(_render_market_context(detail.market_context_snapshots))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_bullets(values: list[str]) -> list[str]:
    if not values:
        return ["- None"]
    return [f"- {value}" for value in values]


def _render_market_context(snapshots: list[MarketContextSnapshot]) -> list[str]:
    if not snapshots:
        return ["- None"]
    return [
        (
            "- "
            f"Market context snapshot id: {snapshot.id}; "
            f"context type: {snapshot.context_type}; "
            f"source: {snapshot.source}; "
            f"source ref: {_format_optional_value(snapshot.source_ref)}; "
            f"observed at: {snapshot.observed_at.isoformat()}; "
            f"captured at: {snapshot.captured_at.isoformat()}"
        )
        for snapshot in snapshots
    ]


def _format_optional_decimal(value: Decimal | None) -> str:
    return "N/A" if value is None else str(value)


def _format_optional_value(value: object | None) -> str:
    return "N/A" if value is None else str(value)
