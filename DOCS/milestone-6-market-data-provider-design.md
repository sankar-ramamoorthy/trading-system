---
title: Milestone 6 Market Data Provider Design
status: complete
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

## Final Sequencing

Milestone 6 is complete. The project can now pivot to ADR-008 API-first web product implementation.

The completed sequence is:

1. `yfinance` daily OHLCV snapshot fetch: complete.
2. Provider-boundary hardening: complete as Milestone 6B Issue 1.
3. Massive.com provider planning: accepted in ADR-009.
4. Massive.com daily bars adapter: complete as Milestone 6C Issue 2.
5. Milestone 6 closeout: complete as Milestone 6D.
6. ADR-008 implementation: next accepted direction.

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

Massive.com is accepted as the next provider candidate after yfinance in ADR-009.

The first Massive.com plan should stay inside the existing Milestone 6 boundary:

- read-only market data only
- explicit user-invoked fetches
- daily OHLCV or daily aggregate bars first
- output stored as `MarketContextSnapshot`
- no provider objects leaking into domain entities or rule evaluation
- no live streaming, execution-grade quotes, automatic refresh, broker integration, recommendations, or AI/ML interpretation

Credential handling should use environment/configuration boundaries such as `MASSIVE_API_KEY`. API keys must not be stored in snapshots, logs, docs examples, tests, or committed files.

The first implementation should use the official `massive` Python client behind the provider registry. It must preserve the adapter boundary and return application-owned snapshot payloads.

ADR-009 records Massive.com's provider status, credential handling, first data shape, and non-goals.

## Implemented Slice: Milestone 6C Issue 1

Massive.com provider planning is complete.

ADR-009 accepts Massive.com as the next provider candidate and records:

- official `massive` Python client as the preferred first implementation path
- `MASSIVE_API_KEY` as the initial credential boundary
- daily aggregate/OHLCV-style bars as the first data shape
- `MarketContextSnapshot` as the storage boundary
- yfinance remains the default provider until a later decision changes it

No Massive.com dependency or runtime adapter was added by Issue 1.

## Implemented Slice: Milestone 6C Issue 2

The narrow Massive.com daily bars adapter is complete.

The CLI now supports:

```powershell
uv run trading-system fetch-market-data AAPL --provider massive --start 2026-04-01 --end 2026-04-30
```

The implementation uses the official `massive` Python client, reads `MASSIVE_API_KEY` from the local environment, fetches daily aggregate bars, normalizes them into application-owned `daily_ohlcv` payloads, and stores snapshots with `source = "massive"`.

yfinance remains the default provider. There is no fallback between providers.

Milestone 6C Issue 2 closeout is recorded in:

- [Milestone 6C Massive Daily Bars Closeout](milestone-6c-massive-daily-bars-closeout.md)

## Implemented Slice: Milestone 6D

Milestone 6 closeout is complete.

The implemented provider set is:

- yfinance as the default provider
- Massive.com as an explicit credentialed provider through `--provider massive`

Milestone 6D records that the provider boundary is proven with two providers while preserving the snapshot, advisory-data, and non-canonical source-of-truth boundaries.

Milestone 6 closeout is recorded in:

- [Milestone 6 Market Data Provider Closeout](milestone-6-closeout.md)

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
- [ADR-009: Massive.com Provider Boundary](ADR/009-massive-provider-boundary.md)
- [Milestone 6 Market Data Provider Closeout](milestone-6-closeout.md)
- [Milestone 4 Market Context Design](milestone-4-market-context-design.md)
- [Milestone 4 Summary](milestone-4-summary.md)
- [Product Roadmap](product-roadmap.md)
