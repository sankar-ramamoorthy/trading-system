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

The first implementation slice should fetch daily OHLCV data for a user-selected symbol or instrument and store the result as a timestamped market context snapshot.

The workflow should be explicit and user-invoked. It should not run as a background refresh or live data feed.

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
