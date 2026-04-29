---
title: Massive.com Provider Boundary
status: accepted
date: 2026-04-27
tags: [adr, market-data, providers, massive, polygon, boundaries, milestone-6]
---

# ADR-009: Massive.com Provider Boundary

## Status

Accepted

## Context

ADR-007 accepted the first market data provider boundary for Milestone 6. Milestone 6A implemented prototype-grade `yfinance` daily OHLCV snapshots. Milestone 6B hardened provider selection so `fetch-market-data` resolves providers through a registry instead of constructing yfinance directly in the CLI.

The next provider candidate is Massive.com, formerly Polygon.io. The official Python client is published as `massive` and supports REST and WebSocket APIs. Massive's public client documentation says Polygon.io rebranded as Massive.com on 2025-10-30, existing API keys/accounts/integrations continue, newer SDKs default to `api.massive.com`, and `api.polygon.io` remains supported for an extended period.

The project needs a provider-specific boundary before adding the dependency, credential handling, or adapter code.

## Decision

Massive.com is accepted as the next market data provider candidate after yfinance.

The first Massive.com implementation should:

- use the official `massive` Python client behind the existing provider registry
- require a local API key from configuration or environment, initially `MASSIVE_API_KEY`
- keep API keys out of snapshots, logs, docs examples, tests, and committed files
- fetch daily aggregate/OHLCV-style stock bars only in the first implementation slice
- normalize provider results into application-owned `daily_ohlcv` `MarketContextSnapshot` payloads where practical
- store `source = "massive"` on Massive-backed snapshots
- include stable source references with symbol, date range, interval or timespan, provider, and adjustment setting when applicable
- keep yfinance available as the default provider until a later decision explicitly changes the default

Provider data remains read-only, advisory, and non-canonical. Massive.com does not define trade meaning, thesis validity, trade approval, or execution action.

## Required Behavior

The first Massive.com provider implementation must:

- be explicit and user-invoked
- work through `fetch-market-data --provider massive`
- fail clearly when `MASSIVE_API_KEY` is missing
- fail clearly when the provider is unavailable, rate-limited, unauthorized, or returns invalid or empty data
- use fake provider responses in tests, not live network calls
- leave existing trade, position, review, rule, and lifecycle records unchanged when provider fetches fail
- keep full payload inspection in context inspection workflows such as `show-context`

## Not Allowed

The first Massive.com implementation must not add:

- live streaming data
- execution-grade quote workflows
- options chains
- news, fundamentals, dividends, splits, or earnings calendars
- automatic refresh daemons
- fallback from Massive.com to yfinance or yfinance to Massive.com
- provider-driven recommendations
- thesis claim verification
- AI or ML interpretation
- broker integration
- automatic trade, thesis, plan, review, rule, or lifecycle mutation
- provider-specific objects in the domain model

## Rationale

Massive.com is a stronger provider candidate than yfinance for future market data work, but adding it should still preserve the snapshot and source-of-truth boundary.

Using the official Python client reduces custom HTTP plumbing and follows the provider's current SDK direction. Keeping the client behind the existing provider registry preserves the ability to replace or supplement providers later.

Starting with daily aggregate/OHLCV bars keeps the first Massive.com slice comparable to the yfinance slice. This tests the provider boundary without expanding into live feeds, options, news, or execution-grade data.

## Consequences

### Positive

- records the credential and provider-status boundary before code is added
- allows the next provider implementation to stay narrow and testable
- keeps yfinance as a prototype/default provider while preparing Massive.com support
- preserves `MarketContextSnapshot` as the application-owned storage boundary

### Trade-Offs

- adds a future dependency on the official `massive` Python client
- requires local API key configuration
- Massive.com access may be limited by subscription, rate limits, entitlement, or plan-specific data availability
- daily bars still do not provide live or execution-grade context

These trade-offs are accepted for Milestone 6C because the goal is read-only provider expansion, not trading automation.

## Follow-Up

The next implementation issue should add a narrow Massive.com daily bars adapter behind the provider registry.

The expected CLI shape is:

```powershell
uv run trading-system fetch-market-data AAPL --provider massive --start 2026-04-01 --end 2026-04-30
```

The implementation should update dependencies, tests, docs, and status after confirming the client package and adapter behavior.

## References

- Massive Python client: https://github.com/massive-com/client-python
- Massive.com: https://massive.com
