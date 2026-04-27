---
title: Market Data Provider Boundary
status: accepted
date: 2026-04-27
tags: [adr, market-data, providers, yfinance, boundaries, milestone-6]
---

# ADR-007: Market Data Provider Boundary

## Status

Accepted

## Context

Milestone 4 introduced read-only `MarketContextSnapshot` records through explicit local JSON import. Those snapshots made market and context information visible during planning and review without making external data canonical trade meaning.

Milestone 5 strengthened review, journal export, and local JSON operations. The system now has enough local workflow and review structure to begin Milestone 6: read-only external market data provider integration.

External provider work needs a durable boundary before implementation because provider data can be delayed, incomplete, rate-limited, subject to licensing limits, or shaped by unstable third-party APIs. Without a boundary, the project could drift into live market data infrastructure, execution signals, or provider-specific domain coupling.

## Decision

The first external market data provider boundary is accepted for Milestone 6.

The first provider stance is:

- `yfinance` may be used as an optional, prototype-grade provider adapter.
- `yfinance` is not treated as production-grade market data infrastructure.
- The first data shape is daily OHLCV history only.
- Provider output must be stored as explicit `MarketContextSnapshot` records before the rest of the application uses it.
- Provider response objects and schemas must not leak into domain entities, services outside the adapter boundary, read models, or rule evaluation.

Provider data remains advisory and non-canonical.

The application remains the source of truth for trade meaning: `TradeIdea`, `TradeThesis`, `TradePlan`, `Position`, `Fill`, `RuleEvaluation`, `Violation`, `TradeReview`, and lifecycle state.

Market data providers supply market facts with caveats. They do not define why a trade exists, whether a thesis is valid, or what the trader should do.

## Required Behavior

Provider-backed workflows must:

- be explicit and user-invoked
- fetch daily OHLCV data only in the first implementation slice
- record source, source reference, observed time or range, captured time, context type, and payload in stored snapshots
- fail clearly when the provider is unavailable or returns invalid data
- leave existing trade, position, review, rule, and lifecycle records unchanged when provider fetches fail
- keep full payload inspection in context inspection workflows such as `show-context`

## Not Allowed

The first provider implementation must not add:

- live streaming data
- intraday execution-grade quotes
- broker integration
- execution triggers
- automatic refresh daemons
- provider-driven trade recommendations
- automatic plan, thesis, review, rule, or lifecycle mutation
- AI or ML interpretation of provider data
- provider-specific objects in the domain model

## Rationale

Daily OHLCV is useful for swing-trading context while avoiding the freshness expectations and operational complexity of live quotes or streaming data.

Using `yfinance` as a prototype provider allows local experimentation without committing to a paid vendor or production feed. Treating it as prototype-grade keeps the reliability and licensing caveats visible.

Storing provider results as `MarketContextSnapshot` records preserves auditability. A review can later inspect what context was captured at the time without depending on the provider still returning the same data.

## Consequences

### Positive

- enables the first real market data integration without weakening the domain model
- keeps external data behind an adapter boundary
- preserves local-first auditability through snapshots
- allows future providers to replace or supplement `yfinance`
- avoids live-feed and execution-system complexity

### Trade-Offs

- `yfinance` may be unreliable, delayed, incomplete, rate-limited, or subject to upstream changes
- daily OHLCV is less useful for intraday decisions than quote or streaming data
- provider data requires validation and clear failure handling before storage
- production-grade provider selection remains future work

These trade-offs are accepted for the first Milestone 6 provider slice because the goal is read-only context, not execution-grade market infrastructure.

## Follow-Up

The first implementation issue should add a narrow provider adapter for daily OHLCV snapshots and CLI access for explicit fetch-and-store behavior.

Any later expansion to live quotes, intraday bars, options chains, news, earnings calendars, paid data vendors, scheduled refresh, or provider reconciliation should be planned separately and may require another ADR if it changes the architecture boundary.
