# Project - Implementation Context

## Current Milestone

Milestone 5 - Review, learning, and local operations

## Current Slice

Select the first narrow Milestone 5 slice after closing Milestone 4.

## Constraints

- Context is read-only support for judgment and review.
- Context interactions are explicit and user-invoked.
- Stored context is a timestamped snapshot or cached reference, not a live feed.
- External context does not define canonical trade meaning.
- No broker integration, execution triggers, streaming, or automated plan creation.
- No AI or ML decision-making.
- External provider adapters such as yfinance are deferred until an ADR records the provider boundary.
- Milestone 5 work must stay journal-grade, local-first, explicit, and auditable.
- Avoid broad portfolio analytics, optimization systems, cloud operations, or generated coaching.

## Next Steps

- Choose the first Milestone 5 issue from review tagging/filtering, narrow journal export, or local backup guidance.
- Keep reporting scoped to completed trades and explicit review records.
- Preserve the distinction between canonical trade records, read-only market context, and derived read models.
- Use the context source port for any future provider adapters without coupling services to provider APIs.
- Add an ADR before implementing yfinance or any other external provider.
- Keep context output visibly separate from `TradeIdea`, `TradeThesis`, `TradePlan`, `Position`, `Fill`, and `TradeReview` meaning.

## Design Context

See the external knowledge base for rationale, open questions, and synthesis:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

Keep this file focused on what code should be written next. Put exploratory reasoning in the knowledge base and durable architectural decisions in `DOCS/` or `DOCS/ADR/`.
