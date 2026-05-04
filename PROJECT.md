# Project - Implementation Context

## Current Milestone

Milestones 1 through 15 are complete. Milestone 16 is the next planned slice: Finqual Fundamentals Provider.

## Current Slice

Milestone 16 should add Finqual as a read-only fundamentals and ownership provider behind the existing `MarketContextSnapshot` boundary. It must not add automatic provider fallback, recommendations, AI interpretation, portfolio analytics, or trade mutation.

## Constraints

- Context is read-only support for judgment and review.
- Context interactions are explicit and user-invoked.
- Stored context is a timestamped snapshot or cached reference, not a live feed.
- External context does not define canonical trade meaning.
- No real-money execution, execution triggers, streaming, or automated plan creation.
- Paper execution is CLI-only and requires existing local `OrderIntent` and open `Position` records.
- No AI or ML decision-making.
- External provider adapters such as yfinance and Massive.com must stay behind the accepted ADR-007 and ADR-009 boundaries.
- Alpaca market data provider work must stay separate from Alpaca broker execution.
- Finqual fundamentals provider work must remain advisory external context, not trade meaning.
- Market data provider work must stay read-only, local-first, explicit, and auditable unless a later ADR changes the boundary.
- No automatic fallback between yfinance, Massive.com, Alpaca, Finqual, or other providers.
- Avoid broad portfolio analytics, optimization systems, cloud operations, generated coaching, or provider-driven trade meaning.

## Next Steps

- Use `DOCS/product-roadmap.md` as the high-level sequencing guide.
- Treat Milestone 15 Alpaca read-only market/options data provider work as complete.
- Treat Milestone 16 as Finqual read-only fundamentals and ownership provider work.
- Move broker UI expansion later: Milestone 17 read-only API/web broker visibility, then Milestone 18 browser paper execution controls.
- Preserve the Milestone 11 boundary: no FastAPI or React broker controls until provider gaps are handled and the broker UI milestones are explicitly accepted.
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
