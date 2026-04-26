# Project - Implementation Context

## Current Milestone

Milestone 4 - Read-only market context

## Current Slice

Decide the next Milestone 4 follow-up after local context import, detail surfacing, discovery filters, and copy-to-target support.

## Constraints

- Context is read-only support for judgment and review.
- Context interactions are explicit and user-invoked.
- Stored context is a timestamped snapshot or cached reference, not a live feed.
- External context does not define canonical trade meaning.
- No broker integration, execution triggers, streaming, or automated plan creation.
- No AI or ML decision-making.
- External provider adapters such as yfinance are deferred until an ADR records the provider boundary.

## Next Steps

- Evaluate whether the current local snapshot workflow is sufficient for Milestone 4 closeout.
- If another Milestone 4 issue is needed, prefer context export/reporting or payload display ergonomics before external providers.
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
