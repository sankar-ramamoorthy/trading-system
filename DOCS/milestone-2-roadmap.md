---
title: Milestone 2 Roadmap
version: v2
date: 2026-04-24
tags: [milestone-2, roadmap, trading-system]
---

# Milestone 2 Roadmap

## Overview

Milestone 2 builds on the completed Milestone 1 MVP and is already partially implemented in the repository.

The goal is to make the system more practical for real use while preserving the domain boundaries established in Milestone 1.

Milestone 2 focuses on:

- durable persistence
- retrieval of prior trades and positions
- clearer separation between intended execution and actual execution
- basic financial visibility
- practical CLI usability

Milestone 2 should not expand into broker integration, market data ingestion, AI systems, dashboards, or broad analytics platforms.

## Guiding Principles

- Extend the domain without distorting it.
- Preserve separation of intent, execution intent, execution fact, outcome, and review.
- Keep the modular monolith architecture.
- Prefer simple vertical improvements over broad infrastructure.
- Add external integrations only after the internal model is stable.

## Observed Progress

Verified against the application repo and tests on 2026-04-24:

- durable local JSON persistence is implemented
- persisted retrieval commands for positions, position detail, and position timeline are implemented
- narrow `OrderIntent` support is implemented between approved `TradePlan` and manual `Fill`
- minimal realized P&L is implemented on the read side for closed positions
- practical write-side CLI commands now exist for the core lifecycle

The main remaining Milestone 2 work is polish, documentation accuracy, and any explicitly scoped follow-on read or usability improvements.

## Work Areas

### Durable Persistence

Current state:

- implemented first as local JSON persistence in `.trading-system/store.json`
- persisted workflow includes `TradeIdea`, `TradeThesis`, `TradePlan`, `Position`, `Fill`, `TradeReview`, `LifecycleEvent`, `RuleEvaluation`, `Violation`, and `OrderIntent`
- repository interfaces remain narrow and stable

Later options when justified:

- SQLite
- Postgres
- migrations

### Query And Retrieval Workflows

Implemented commands:

- `list-trade-ideas`
- `list-trade-plans`
- `show-trade-plan`
- `list-positions`
- `show-position`
- `show-position-timeline`

Current read-side views expose linked plans, ideas, theses, fills, reviews, order intents, and realized P&L where applicable.

### OrderIntent

Current state:

- implemented narrowly as the bridge between approved `TradePlan` and manual `Fill`
- preserves the distinction between intended execution and actual execution
- remains a system intent record, not a broker-order model
- fills can optionally reference an `OrderIntent`

Broker integration remains out of scope for this step.

### Basic P&L

Current state:

- implemented narrowly on the read side for closed positions based on persisted fills
- not persisted as a canonical field
- intentionally simple and auditable

Still deferred:

- tax lots
- commissions and fees
- portfolio aggregation
- advanced performance reporting

### Lifecycle Timeline

Implemented command:

```powershell
uv run trading-system show-position-timeline <position-id>
```

### CLI Usability

Implemented core workflow commands:

- `create-trade-idea`
- `create-trade-thesis`
- `create-trade-plan`
- `approve-trade-plan`
- `evaluate-trade-plan-rules`
- `create-order-intent`
- `open-position`
- `record-fill`
- `create-trade-review`

The demo command remains useful as a smoke path, but Milestone 2 is no longer demo-only.

## Explicitly Deferred

The following remain out of scope for Milestone 2 unless a future ADR changes the boundary:

- broker integration
- automated execution
- real-time market data
- AI-generated insights
- dashboards or web UI
- portfolio-level analytics
- advanced reporting
- strategy automation

## Exit Criteria

Milestone 2 is complete when:

- core data persists across runs
- past positions and trades can be retrieved
- intended execution is distinct from actual fills
- basic P&L is available for simple closed trades
- CLI supports practical manual usage
- documentation reflects actual behavior

Most of these conditions are now implemented in code. Documentation alignment was one of the remaining visible gaps in the application repo as of 2026-04-24.

## Final Note

Milestone 2 should make the MVP practical without weakening the domain model.

Milestone 2 is followed by the accepted Milestones 3-5 roadmap documented in `DOCS/milestones-3-to-5-roadmap.md`:

- Milestone 3: Manual Workflow Usability
- Milestone 4: Read-Only Market Context
- Milestone 5: Review, Learning, and Local Operations

An exploratory reinforcement-learning note exists in the linked knowledge base, but it is deferred beyond this roadmap and is not the next repository milestone.
