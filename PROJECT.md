# Project - Implementation Context

## Current Milestone

Milestone 13 is in closeout. Alpaca paper trading is now available behind the existing broker port and CLI paper-order commands.

## Current Slice

Milestone 13 added the Alpaca paper adapter through core services and CLI only. The slice keeps browser controls, API broker endpoints, reconciliation, and real-money execution out of scope.

## Constraints

- Context is read-only support for judgment and review.
- Context interactions are explicit and user-invoked.
- Stored context is a timestamped snapshot or cached reference, not a live feed.
- External context does not define canonical trade meaning.
- No real-money execution, execution triggers, streaming, or automated plan creation.
- Paper execution is CLI-only and requires existing local `OrderIntent` and open `Position` records.
- No AI or ML decision-making.
- External provider adapters such as yfinance and Massive.com must stay behind the accepted ADR-007 and ADR-009 boundaries.
- Market data provider work must stay read-only, local-first, explicit, and auditable unless a later ADR changes the boundary.
- Avoid broad portfolio analytics, optimization systems, cloud operations, generated coaching, or provider-driven trade meaning.

## Next Steps

- Use `DOCS/post-milestone-11-roadmap.md` as the high-level sequencing guide.
- Close Milestone 13 after full-suite validation and status updates.
- Treat future broker work as Milestone 14 reconciliation/status sync, not browser execution controls.
- Preserve the Milestone 11 boundary: no FastAPI or React broker controls until the CLI paper workflow is proven sufficient.
- Keep `fetch-market-data` scoped to read-only daily OHLCV snapshots unless a new issue explicitly expands provider scope.
- Preserve the distinction between canonical trade records, read-only market context, and derived read models.
- Keep provider response objects and schemas out of domain logic.
- Keep broker response objects behind the broker port; local `BrokerOrder` and `Fill` records remain canonical for internal audit.
- Keep market context output visibly separate from `TradeIdea`, `TradeThesis`, `TradePlan`, `Position`, `Fill`, and `TradeReview` meaning.
- Extend coverage only where it protects the provider boundary or linked snapshot handling.
- Keep review export and local JSON operations factual and explicit.

## Design Context

See the external knowledge base for rationale, open questions, and synthesis:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

Keep this file focused on what code should be written next. Put exploratory reasoning in the knowledge base and durable architectural decisions in `DOCS/` or `DOCS/ADR/`.
