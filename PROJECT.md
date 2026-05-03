# Project - Implementation Context

## Current Milestone

Milestone 12 is complete. Active direction: choose and plan Milestone 13 before adding live Alpaca paper calls.

## Current Slice

Milestone 12 hardened broker-order inspection, audit visibility, and simulated paper lifecycle coverage through core services and CLI only.

## Constraints

- Context is read-only support for judgment and review.
- Context interactions are explicit and user-invoked.
- Stored context is a timestamped snapshot or cached reference, not a live feed.
- External context does not define canonical trade meaning.
- No live broker integration, real-money execution, execution triggers, streaming, or automated plan creation.
- Simulated paper execution is CLI-only and requires existing local `OrderIntent` and open `Position` records.
- No AI or ML decision-making.
- External provider adapters such as yfinance and Massive.com must stay behind the accepted ADR-007 and ADR-009 boundaries.
- Market data provider work must stay read-only, local-first, explicit, and auditable unless a later ADR changes the boundary.
- Avoid broad portfolio analytics, optimization systems, cloud operations, generated coaching, or provider-driven trade meaning.

## Next Steps

- Use `DOCS/post-milestone-11-roadmap.md` as the high-level sequencing guide.
- Choose and plan Milestone 13 before expanding broker execution.
- Keep future Alpaca work behind the accepted broker port and local secret-vault boundary.
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
