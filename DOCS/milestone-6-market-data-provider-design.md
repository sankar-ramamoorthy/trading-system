---
title: Milestone 6 Market Data Provider Design
status: accepted-for-roadmap
date: 2026-04-27
tags: [milestone-6, market-data, providers, yfinance, design, trading-system]
---

# Milestone 6 Market Data Provider Design

## Purpose

Milestone 6 introduces the first read-only external market data provider integration.

The purpose is to make real market data available as explicit local context snapshots while preserving the existing source-of-truth boundary: the trading system owns trade meaning, and providers supply market facts with caveats.

## Accepted Boundary

ADR-007 accepts the provider boundary for Milestone 6:

- first provider stance: optional prototype-grade `yfinance`
- first data shape: daily OHLCV history
- provider output is stored as `MarketContextSnapshot`
- provider data is advisory and non-canonical
- provider failures do not block core trade workflow

## First Implementation Target

The first implementation slice, Milestone 6A, is complete. It is implemented as `fetch-market-data`, which fetches daily OHLCV data for a user-selected symbol or instrument and stores the result as a timestamped market context snapshot.

The workflow should be explicit and user-invoked. It should not run as a background refresh or live data feed.

## Implemented Slice: Milestone 6A

- `fetch-market-data <symbol> --start YYYY-MM-DD --end YYYY-MM-DD`
- optional `--instrument-id`, `--target-type`, and `--target-id` linking
- `daily_ohlcv` snapshot payloads with raw OHLCV plus adjusted close

Milestone 6A closeout is recorded in:

- [Milestone 6A Yfinance Market Data Closeout](milestone-6a-yfinance-market-data-closeout.md)

## Next Sequencing

Milestone 6 should be finished before the project pivots to ADR-008 API-first web product implementation.

The current sequence is:

1. `yfinance` daily OHLCV snapshot fetch: complete.
2. Provider-boundary hardening: complete as Milestone 6B Issue 1.
3. Massive.com provider planning: evaluate Massive.com, formerly Polygon.io, as the next provider candidate.
4. Milestone 6 closeout: record the provider boundary status and the accepted next-provider direction.
5. ADR-008 implementation: begin FastAPI/React trade-capture draft work after Milestone 6 is closed or explicitly paused.

## Implemented Slice: Milestone 6B Issue 1

Provider-boundary hardening is complete.

The CLI now supports explicit provider selection while preserving yfinance as the default:

```powershell
uv run trading-system fetch-market-data AAPL --provider yfinance --start 2026-04-01 --end 2026-04-30
```

The implementation adds a provider registry so CLI code resolves a provider-backed source adapter, source name, and source reference before calling the existing market-context import service.

Milestone 6B closeout is recorded in:

- [Milestone 6B Provider Boundary Hardening Closeout](milestone-6b-provider-boundary-hardening-closeout.md)

## Massive.com Planning Direction

Massive.com should be considered as the next provider candidate after yfinance.

The first Massive.com plan should stay inside the existing Milestone 6 boundary:

- read-only market data only
- explicit user-invoked fetches
- daily OHLCV or daily aggregate bars first
- output stored as `MarketContextSnapshot`
- no provider objects leaking into domain entities or rule evaluation
- no live streaming, execution-grade quotes, automatic refresh, broker integration, recommendations, or AI/ML interpretation

Credential handling should use environment/configuration boundaries such as `MASSIVE_API_KEY`. API keys must not be stored in snapshots, logs, or committed files.

The provider plan should decide whether to use the official Python client or direct REST. Either approach must preserve the adapter boundary and return application-owned snapshot payloads.

Adding Massive.com may require a companion ADR or an ADR-007 update if it changes provider status, credential handling, fallback behavior, or supported data shapes.

## Non-Goals

Milestone 6 should not introduce:

- live streaming market data
- execution-grade quotes
- broker integration
- execution triggers
- automatic plan or thesis updates
- provider-driven recommendations
- AI or ML interpretation
- provider objects in domain logic

## Related Documents

- [ADR-007: Market Data Provider Boundary](ADR/007-market-data-provider-boundary.md)
- [Milestone 4 Market Context Design](milestone-4-market-context-design.md)
- [Milestone 4 Summary](milestone-4-summary.md)
- [Product Roadmap](product-roadmap.md)
