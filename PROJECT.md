# Project - Implementation Context

## Current Milestone

Milestone 7 has started. Active direction: ADR-008 API-first web product and trade-capture draft workflow.

## Current Slice

Milestone 7B is complete. The next implementation slice is Milestone 7C: Trade Capture Draft Contract.

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

- Plan and implement Milestone 7C: Trade Capture Draft Contract.
- Continue Milestone 7 through the documented issue map in `DOCS/milestone-7-issue-map.md`.
- Preserve the 7B boundary: lookup is complete; draft contracts, parsing, and save workflow remain later 7.x issues.
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
