# Project - Implementation Context

## Current Milestone

Milestone 4 - Read-only market context

## Current Slice

Implement the initial read-only context retrieval workflow for instrument, planning, position, or review snapshots.

## Constraints

- Context is read-only support for judgment and review.
- Context interactions are explicit and user-invoked.
- Stored context is a timestamped snapshot or cached reference, not a live feed.
- External context does not define canonical trade meaning.
- No broker integration, execution triggers, streaming, or automated plan creation.
- No AI or ML decision-making.

## Next Steps

- Define a narrow context retrieval port.
- Add a simple infrastructure adapter, starting with a stub or local snapshot source.
- Add local persistence for timestamped context snapshots if the first slice needs stored inspection.
- Add CLI commands to fetch or refresh context and inspect preserved context.
- Keep context output visibly separate from `TradeIdea`, `TradeThesis`, `TradePlan`, `Position`, `Fill`, and `TradeReview` meaning.

## Design Context

See the external knowledge base for rationale, open questions, and synthesis:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

Keep this file focused on what code should be written next. Put exploratory reasoning in the knowledge base and durable architectural decisions in `DOCS/` or `DOCS/ADR/`.
