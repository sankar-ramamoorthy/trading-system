# Project - Implementation Context

## Current Milestone

Milestone 6 is complete. Next accepted direction: ADR-008 API-first web product and trade-capture draft workflow.

## Current Slice

Milestone 6D closeout is complete. The next implementation slice should be planned from ADR-008.

## Constraints

- Context is read-only support for judgment and review.
- Context interactions are explicit and user-invoked.
- Stored context is a timestamped snapshot or cached reference, not a live feed.
- External context does not define canonical trade meaning.
- No broker integration, execution triggers, streaming, or automated plan creation.
- No AI or ML decision-making.
- External provider adapters such as yfinance and Massive.com must stay behind the accepted ADR-007 and ADR-009 boundaries.
- Market data provider work must stay read-only, local-first, explicit, and auditable unless a later ADR changes the boundary.
- Avoid broad portfolio analytics, optimization systems, cloud operations, generated coaching, or provider-driven trade meaning.

## Next Steps

- Begin ADR-008 API-first web product and trade-capture draft planning/implementation.
- Keep `fetch-market-data` scoped to read-only daily OHLCV snapshots unless a new issue explicitly expands provider scope.
- Preserve the distinction between canonical trade records, read-only market context, and derived read models.
- Keep provider response objects and schemas out of domain logic.
- Keep market context output visibly separate from `TradeIdea`, `TradeThesis`, `TradePlan`, `Position`, `Fill`, and `TradeReview` meaning.
- Extend coverage only where it protects the provider boundary or linked snapshot handling.
- Keep review export and local JSON operations factual and explicit.

## Design Context

See the external knowledge base for rationale, open questions, and synthesis:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

Keep this file focused on what code should be written next. Put exploratory reasoning in the knowledge base and durable architectural decisions in `DOCS/` or `DOCS/ADR/`.
