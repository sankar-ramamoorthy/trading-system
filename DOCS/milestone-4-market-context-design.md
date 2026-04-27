---
title: Milestone 4 Market Context Design
status: complete
date: 2026-04-24
tags: [milestone-4, market-context, design, trading-system]
---

# Milestone 4 Market Context Design

## Purpose

Milestone 4 adds read-only market and context information to support trade planning and post-trade review.

The purpose is to make the system more informed without weakening the canonical domain model. External context may inform a decision, but it does not define what a trade means inside the system.

## Source-Of-Truth Boundary

- market and context inputs are external and read-only
- the trading system remains the canonical source of truth for `TradeIdea`, `TradeThesis`, `TradePlan`, `Position`, `Fill`, `RuleEvaluation`, `Violation`, and `TradeReview`
- external context does not become canonical trade meaning
- context is support for planning and review, not a replacement for explicit trader-authored intent

## Allowed Data Types

Milestone 4 may include narrowly scoped read-only data such as:

- price history snapshots
- end-of-day or delayed quote context
- benchmark or sector reference data
- calendar context such as earnings dates or macro event dates
- user-curated annotations or imported context references tied to planning or review

Any included data must stay explainable, auditable, and non-executing.

## Storage And Snapshot Expectations

- context should be stored locally when needed for later inspection or review
- stored context should behave as a snapshot or cached reference, not as a live canonical feed
- snapshots should be timestamped clearly enough to preserve auditability
- storage should remain local-first and narrow in scope

## CLI And Read-Model Expectations

Expected high-level workflow shape:

- fetch or refresh read-only context for an instrument or review target
- inspect context from the CLI during planning
- inspect preserved context during post-trade review
- surface context in read models as supporting information, separate from the canonical trade record

The CLI should make the separation obvious: context is shown alongside a trade, not merged into the trade's domain meaning.

## Initial Implementation Slice

The first repository slice uses explicit local JSON file import as the context source.

This keeps the workflow local-first and auditable while introducing the durable boundary needed for later provider adapters:

- imported files become stored `MarketContextSnapshot` records
- each snapshot is linked to an instrument and may optionally link to a trade plan, position, or trade review target
- the imported payload remains flexible JSON
- external providers were deferred until a small ADR recorded provider status, failure behavior, and non-canonical use; ADR-007 now records that boundary for Milestone 6

Follow-up slices now add practical discovery and reuse:

- `list-context` supports broad discovery with optional filters for instrument, target, context type, source, observed range, and captured range
- linked snapshots appear as metadata-only context sections in trade plan, position, and trade review detail views
- `copy-context` creates a new immutable linked snapshot from an existing one without mutating the original import

## Closeout

Milestone 4 closed on 2026-04-26 with the local snapshot workflow implemented and validated.

The completed scope includes:

- explicit local JSON import into stored `MarketContextSnapshot` records
- optional links from snapshots to `TradePlan`, `Position`, and `TradeReview` targets
- metadata-only context sections in trade plan, position, and trade review detail views
- full payload inspection through `show-context`
- broad `list-context` discovery filters
- `copy-context` reuse that creates a new immutable linked snapshot
- documentation that keeps context read-only, advisory, auditable, and non-canonical

This is sufficient for the Milestone 4 completion criteria in `DOCS/milestones-3-to-5-roadmap.md`.

## Non-Goals

- live streaming market data
- execution triggers
- broker integration or broker-driven context
- automated plan creation from external signals
- external context overriding trader-authored thesis or plan
- context ingestion turning into a general research platform

## Likely Future ADR Trigger

ADR-007 now records the durable market data provider boundary for Milestone 6. Further ADRs should be introduced if provider scope expands into live feeds, scheduled refresh, paid vendor selection, options chains, or another boundary that materially affects long-term architecture.
