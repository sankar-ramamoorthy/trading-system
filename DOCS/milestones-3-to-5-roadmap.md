---
title: Milestones 3 To 5 Roadmap
status: accepted
date: 2026-04-24
tags: [roadmap, milestone-3, milestone-4, milestone-5, trading-system]
---

# Milestones 3 To 5 Roadmap

## Current Status

- Milestone 1 is complete.
- Milestone 2 is complete.
- Milestone 3 is complete.
- Milestone 4 is complete.
- Milestone 5 is complete.
- Milestone 6 has started with ADR-007 for the market data provider boundary.

## Accepted Sequence

The accepted roadmap after Milestone 2 is:

1. Milestone 3: Manual Workflow Usability
2. Milestone 4: Read-Only Market Context
3. Milestone 5: Review, Learning, and Local Operations

## Rationale For The Order

- Stabilize daily manual usage first so the core workflow is practical without adding new external dependencies.
- Add read-only market and context inputs only after the manual workflow is usable enough to benefit from them.
- Deepen review, reporting, and local operational robustness after the workflow and inputs have settled.

## Explicit Deferrals

The following are deferred beyond this roadmap:

- Postgres as the active backend
- broker integration
- FastAPI
- reinforcement learning
- live automation

Reinforcement learning remains exploratory and would require a new ADR and a separate milestone set later.

## Milestone 3: Manual Workflow Usability

### Objective

Make the existing manual CLI workflow efficient enough for routine day-to-day use without changing core domain boundaries.

### Key Deliverables

- CLI polish for common write and read paths
- better command ergonomics and output clarity
- reduced friction in moving from plan to execution to review
- practical usability improvements that keep the workflow explicitly manual

### Explicit Non-Goals

- new external integrations
- broker connectivity
- market data ingestion
- web UI or API expansion
- analytics platform work

### Completion Criteria

- routine manual trade workflows require fewer awkward or repetitive steps
- CLI output is clearer for planning, execution, and review tasks
- usability improvements do not blur the boundaries between intent, execution, and review
- the manual workflow remains auditable and explicit

## Milestone 4: Read-Only Market Context

### Objective

Introduce read-only market and context support that helps planning and review while preserving the system as the canonical owner of trade meaning.

### Key Deliverables

- read-only retrieval of selected market and context inputs
- local snapshot or caching behavior suitable for later review
- CLI access to context alongside trade planning and review workflows
- explicit source-of-truth boundaries between external context and internal trade meaning

### Explicit Non-Goals

- live streaming
- execution triggers
- broker coupling
- external systems becoming canonical trade meaning
- automated trading behavior

### Completion Criteria

- context can be viewed and referenced during planning and review
- external context remains read-only and non-canonical
- the system can preserve enough context locally for audit and retrospective use
- milestone scope does not expand into automation or integration sprawl

### Closeout Status

Milestone 4 is complete as of 2026-04-26.

The implementation uses explicit local JSON imports stored as immutable `MarketContextSnapshot` records. Snapshots can be linked to trade plans, positions, and trade reviews, listed with discovery filters, inspected directly, and copied to a new target without mutating the original snapshot.

External market data provider implementation was deferred until an ADR recorded provider status, failure behavior, and non-canonical use. ADR-007 now records that boundary for Milestone 6.

## Milestone 5: Review, Learning, And Local Operations

### Objective

Strengthen post-trade review, journal-grade reporting, export, and local operational robustness without turning the project into a portfolio engine.

### Key Deliverables

- review tagging and filtering
- narrow reporting and export workflows
- local backup and operational support for the local-first workflow
- practical robustness improvements for running and maintaining the system locally

### Explicit Non-Goals

- portfolio-engine expansion
- broad analytics sprawl
- AI-generated review or coaching
- reinforcement learning
- cloud-first operations

### Completion Criteria

- reviews can be categorized and filtered in useful ways
- journal-grade reports or exports exist for local use
- local operational workflows are clear enough for backup, restore, and practical maintenance
- review and reporting features remain narrow, auditable, and aligned with the manual trading workflow

## Milestone 6 Transition

Milestone 6 begins after this roadmap with read-only market data provider integration. ADR-007 accepts optional prototype-grade `yfinance` as the first provider stance and daily OHLCV history as the first data shape. Provider output must remain advisory, non-canonical, and stored as `MarketContextSnapshot` records.
