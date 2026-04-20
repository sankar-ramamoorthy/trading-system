---
title: Milestone 2 Roadmap
version: v1
date: 2026-04-20
tags: [milestone-2, roadmap, trading-system]
---

# Milestone 2 Roadmap

## Overview

Milestone 2 builds on the completed Milestone 1 MVP.

The goal is to make the system more practical for real use while preserving the domain boundaries established in Milestone 1.

Milestone 2 should focus on:

- durable persistence
- retrieving prior trades and positions
- clearer separation between intended execution and actual execution
- basic financial visibility
- CLI usability improvements

Milestone 2 should not expand into broker integration, market data ingestion, AI systems, dashboards, or broad analytics platforms.

## Guiding Principles

- Extend the domain without distorting it.
- Preserve separation of intent, execution, outcome, and review.
- Keep the modular monolith architecture.
- Prefer simple vertical improvements over broad infrastructure.
- Add external integrations only after the internal model is stable.

## Candidate Work Areas

### Durable Persistence

Replace in-memory demo repositories with durable persistence.

Initial scope should include:

- `TradeIdea`
- `TradeThesis`
- `TradePlan`
- `Position`
- `Fill`
- `TradeReview`
- `LifecycleEvent`

Repository interfaces should remain stable where possible.

### Query And Retrieval Workflows

Add simple read workflows for past trades and positions.

Potential CLI commands:

- list positions
- show position
- list closed positions
- show associated fills and review

### OrderIntent

Introduce `OrderIntent` as the bridge between planned execution and actual fills.

This preserves the distinction between:

- what the trader intended to execute
- what actually filled

Broker integration remains out of scope for this step.

### Basic P&L

Add minimal realized P&L for closed positions based on fills.

This should stay simple:

- no tax lots
- no commissions or fees initially
- no advanced performance reporting

### Lifecycle Timeline

Expose lifecycle events in a useful ordered view.

Potential CLI command:

```powershell
uv run trading-system show-position-timeline <position-id>
```

### CLI Usability

Move beyond demo-only usage by adding simple commands for the core lifecycle.

Potential commands:

- create trade idea
- create trade thesis
- create trade plan
- approve plan
- evaluate rules
- open position
- record fill
- create review

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

## Final Note

Milestone 2 should make the MVP practical without weakening the domain model.

The likely next meaningful step is durable persistence plus `OrderIntent`, not external integrations.
