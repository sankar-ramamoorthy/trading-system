# Project - Implementation Context

## Current Milestone

Milestone 5 - Review, learning, and local operations

## Current Slice

Markdown journal export is implemented as the third narrow Milestone 5 slice.

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

- Keep `export-review-journal --output <path>` scoped to completed reviewed trades.
- Reuse existing review filters, including tags and quality scores, for any export follow-on.
- Keep Markdown output factual: review notes, outcome, scores, and linked context metadata.
- Keep overwrite protection and no-file empty results behavior intact.
- Keep future reporting scoped to completed trades and explicit review records.
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
