---
title: MVP Definition and Boundaries
status: accepted
date: 2026-04-20
tags: [adr, mvp, milestone-1, boundaries]
---

# ADR-005: MVP Definition and Boundaries

## Status

Accepted

## Context

Milestone 1 implements a complete local vertical slice:

```text
TradeIdea -> TradeThesis -> TradePlan -> plan approval -> RuleEvaluation -> Position -> Fill -> Position close -> TradeReview
```

`LifecycleEvent` records auditable state transitions throughout this lifecycle.

The system now supports structured trade intent, deterministic rule evaluation, manual execution recording, automatic closure from fills, and manual post-trade review.

At this point, the project needs a clear MVP boundary to prevent premature expansion into brokers, market data, analytics, AI, or UI work before the core domain model is stable.

## Decision

The MVP is defined as:

```text
A local, CLI-driven trading system that enforces structured trade intent,
captures execution through manual fills, closes positions from fills, and
supports manual post-trade review with auditability.
```

The MVP is intentionally manual and local.

It prioritizes:

- discipline over automation
- explicit structure over convenience
- auditability over optimization
- correctness over completeness
- domain clarity over integration breadth

## Included In MVP

The MVP includes:

- `TradeIdea`
- `TradeThesis`
- `TradePlan`
- plan approval state
- deterministic `Rule` evaluation
- `RuleEvaluation`
- `Violation`
- `Position` opened from approved `TradePlan`
- manual `Fill` recording
- position execution-state tracking
- automatic position close when fills reduce open quantity to zero
- one manual `TradeReview` per closed position
- `LifecycleEvent` audit trail
- CLI demo using in-memory repositories

## Explicitly Excluded From MVP

The MVP does not include:

- broker integration
- automated order placement
- order synchronization
- market data ingestion
- historical or real-time price feeds
- AI or ML features
- news, filings, or context ingestion
- reconciliation workflows
- P&L calculations
- commissions, fees, or slippage modeling
- performance analytics
- dashboards or reports
- REST API or web UI
- `OrderIntent`
- multi-leg trades
- reversal workflows
- fill correction or amendment workflows
- force-close or reopen workflows
- trade review editing/versioning
- multiple reviews per position

## Rationale

### Manual Execution

Execution is manual because the system must first prove that it can model trade intent, execution reality, closure, and review correctly.

Broker integration would add external failure modes and coupling before the internal domain model is stable.

### No Broker Integration Yet

External brokers own external facts such as orders and fills. The system owns trade meaning.

Broker integration belongs later as an infrastructure adapter, not as the foundation of the domain model.

### No P&L Or Analytics Yet

P&L and analytics depend on reliable execution state. Milestone 1 establishes fills, quantities, average entry, and closure first.

Analytics should be added only after the system can reliably represent completed trades.

### Simple Immutable Trade Review

Trade review is intentionally manual, structured, and immutable for MVP.

This keeps the audit model simple:

- one review per completed position
- no edit workflow
- no versioning workflow
- no generated review content

Review exists to capture what was learned, not to become a journaling platform or analytics engine.

### CLI-Driven Usage

The CLI is sufficient for MVP because the goal is to validate domain behavior and workflow boundaries.

A UI or API would add surface area without improving the core model.

## Consequences

### Positive

- clear scope
- low integration risk
- strong domain boundaries
- easy local validation
- direct audit trail
- foundation for future persistence and integration

### Trade-Offs

- manual data entry is required
- no live market context
- no broker automation
- no financial performance reporting
- no rich user interface

These trade-offs are accepted for the MVP.

## Future Direction

Post-MVP work may include:

- durable Postgres persistence
- Alembic migrations
- repository implementations
- `OrderIntent`
- read-only market data context
- basic P&L computation
- broker integration as an adapter
- improved review and learning workflows

Each future area should be implemented through explicit issues and, when architectural impact is meaningful, a new ADR.

## Final Boundary

Features outside this MVP definition do not belong in Milestone 1.

Milestone 1 is complete when the system can represent:

```text
what was planned, what happened, when it closed, and what was learned
```

without relying on external integrations.
