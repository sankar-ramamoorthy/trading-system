# Project - Implementation Context

## Current Milestone

Milestone 4 - Read-only market context

## Current Slice

Refine the read-only context snapshot workflow so linked snapshots remain visible in planning, position, and review inspection without becoming canonical trade meaning.

## Constraints

- Context is read-only support for judgment and review.
- Context interactions are explicit and user-invoked.
- Stored context is a timestamped snapshot or cached reference, not a live feed.
- External context does not define canonical trade meaning.
- No broker integration, execution triggers, streaming, or automated plan creation.
- No AI or ML decision-making.
- External provider adapters such as yfinance are deferred until an ADR records the provider boundary.

## Next Steps

- Keep refining the local JSON file import path and detail-view inspection for timestamped context snapshots.
- Use the context source port for future provider adapters without coupling services to provider APIs.
- Add CLI commands and read models only where context remains visibly separate from canonical trade meaning.
- Add an ADR before implementing yfinance or any other external provider.
- Keep context output visibly separate from `TradeIdea`, `TradeThesis`, `TradePlan`, `Position`, `Fill`, and `TradeReview` meaning.

## Design Context

See the external knowledge base for rationale, open questions, and synthesis:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

Keep this file focused on what code should be written next. Put exploratory reasoning in the knowledge base and durable architectural decisions in `DOCS/` or `DOCS/ADR/`.
