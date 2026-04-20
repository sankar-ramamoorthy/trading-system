# trading-system

A professional-grade personal trading system for structured discretionary trading.

## Purpose

This project is designed to help a single trader:

- manage trades with full context
- enforce discipline and process
- monitor thesis and market-context changes
- separate hard rules from interpretive signals
- evolve toward deeper automation without losing control

This is **not** a black-box trading bot and not a generic indicator engine.

## Core Principles

- **Structured trade representation**: every trade should have intent, thesis, timeframe, and lifecycle state
- **Deterministic discipline**: hard rules are explicit, enforceable, and auditable
- **Context-aware intelligence**: market, filing, peer, and macro changes should inform decisions without replacing judgment
- **Canonical domain model**: the system owns trade meaning; external systems provide facts
- **Incremental evolution**: start simple, keep architecture clean, and expand only when justified

## Architecture

The system follows a **modular monolith** architecture with clear internal boundaries.

Implementation uses a Python `src/` layout:

```text
src/trading_system/
```

Primary modules:

- `app/` - CLI entrypoints
- `domain/` - core business entities and domain logic
- `services/` - use-case orchestration
- `rules_engine/` - deterministic rule evaluation
- `ports/` - repository and unit-of-work interfaces
- `infrastructure/` - persistence and adapter implementations

See:

- `DOCS/ADR/001-system-architecture.md`
- `DOCS/ADR/002-rules-vs-context.md`
- `DOCS/ADR/003-development-and-deployment-strategy.md`
- `DOCS/ADR/004-canonical-domain-and-source-of-truth.md`
- `DOCS/ADR/005-mvp-definition-and-boundaries.md`
- `DOCS/domain-model.md`
- `DOCS/milestone-1-summary.md`
- `DOCS/milestone-2-roadmap.md`
- `DOCS/systems-blueprint.md`

## Current Workflow

Milestone 1 implements the first complete thin vertical slice:

```text
TradeIdea -> TradeThesis -> TradePlan -> plan approval -> RuleEvaluation -> Position -> Fill -> Position close -> TradeReview
```

`LifecycleEvent` records auditable state transitions throughout the trade lifecycle.

Implemented local workflows currently support:

- creating a `TradeIdea`
- creating a `TradeThesis` linked to the idea
- creating a `TradePlan` linked to the idea and thesis
- approving a `TradePlan`
- evaluating deterministic rules for an approved plan
- opening a `Position` from an approved plan
- recording manual `Fill` records for an open position
- updating position execution state from fills
- automatically closing a position when reducing fills bring open quantity to zero
- recording a `POSITION_OPENED` lifecycle event
- recording `FILL_RECORDED`, `POSITION_CLOSED`, and `TRADE_REVIEW_CREATED` lifecycle events
- creating one manual `TradeReview` for a closed position

The position workflow preserves the canonical rule that a `Position` originates from a `TradePlan`, not directly from a `TradeIdea`. Position `instrument_id` and `purpose` are derived from the linked idea through the approved plan.

Manual fill recording currently supports the minimum execution state needed for the first vertical slice:

- total bought quantity
- total sold quantity
- current open quantity
- weighted average entry price for current open exposure

Fill recording is manual only. The domain rejects invalid sides, non-positive quantity or price, fills on closed positions, and oversell/reversal attempts.

Position closing is not a separate command. It is a domain state transition caused by execution reality: when a reducing fill brings `current_quantity` to exactly zero, the position moves to `closed`, `closed_at` is set, and the closing fill is recorded.

Trade review is manual and intentionally simple. A review can be created only for a closed position, and Milestone 1 allows one immutable review per position.

## How To Use This System (Milestone 1)

Milestone 1 is CLI-driven. It is a structured discipline and journal tool, not an execution bot.

Execution is manual:

- the trader creates the idea, thesis, and plan
- the trader approves the plan
- deterministic rules are evaluated before execution
- the trader records fills manually
- the position closes when fills reduce open quantity to zero
- the trader creates one manual review for the completed position

Run the canonical Milestone 1 demo:

```powershell
uv run trading-system demo-planned-trade
```

The demo uses in-memory repositories and prints each stage:

1. create trade idea
2. create trade thesis
3. create trade plan
4. approve plan
5. evaluate deterministic rules
6. open position
7. record entry fill
8. record exit fill
9. close position from fills
10. create trade review

The final summary includes approval state, rule evaluation count, violation count, fill count, open quantity, position state, review id, and lifecycle event count.

## What Is The MVP?

The MVP is a local, CLI-driven trading system that enforces structured trade intent, captures execution through manual fills, and supports post-trade review with auditability.

The MVP includes:

- canonical trade intent: `TradeIdea`, `TradeThesis`, `TradePlan`
- deterministic rule evaluation and violation recording
- position opening from an approved trade plan
- manual fill recording
- execution-state tracking on positions
- automatic close when fills reduce open quantity to zero
- one manual trade review per closed position
- lifecycle events for auditable state transitions
- in-memory demo infrastructure for local verification

The MVP explicitly excludes:

- broker integration
- automated order placement
- market data ingestion
- AI or ML features
- P&L, analytics, dashboards, and reporting
- commissions, fees, and slippage modeling
- fill correction or amendment workflows
- manual force-close or reopen workflows
- REST API or web UI

The MVP philosophy is discipline over automation. The system first proves that trade intent, execution reality, closure, and review can be represented correctly before adding external systems or analytics.

## Out of Scope Right Now

The current implementation intentionally does not include:

- broker integration
- market data ingestion
- AI or ML features
- reconciliation workflows
- FastAPI
- broker orders or execution adapters
- commissions, fees, slippage, or P&L engines
- fill correction or amendment workflows
- manual force-close or reopen workflows
- automated reviews, analytics, dashboards, or review editing workflows

## Documentation & Knowledge

This project uses a split-memory system to keep the codebase clean while maintaining deep context.

### 1. Local Repository Documentation (The "How" and "When")
- **ADRs:** Located in `DOCS/ADR/`. These are versioned architectural decisions.
- **System Design:** Detailed blueprints are in `DOCS/`.
- **Status:** Check `DOCS/milestones.md` (if applicable) for current development progress.

### 2. External LLM Wiki (The "Why" and "What")
Permanent project memory, entity definitions, and cross-topic syntheses are maintained in the external Knowledge Base:
`C:\Users\bosto\dockerstuff\knowledge-base\trading-system\`

- **Canonical Entities:** See `knowledge/entities/` in the Wiki for the domain model truth.
- **Process & Rules:** See `knowledge/topics/` for synthesized trading rules and logic.
- **Context Injection:** Before starting an AI coding session, provide the AI with the Wiki's `AGENTS.md` to prime it with long-term project memory.

## Development Approach

- no code without an explicit issue
- work is phase-based and milestone-driven
- architecture and domain clarity come before implementation detail
- Docker is used pragmatically, not dogmatically

## Local Development

This project uses `uv`.

Run the test suite:

```powershell
uv run pytest
```

Run the CLI:

```powershell
uv run trading-system version
```

Run the canonical Milestone 1 demo:

```powershell
uv run trading-system demo-planned-trade
```

The demo uses in-memory repositories and prints each stage of the local workflow: plan approval, rule evaluation, position opening, fill recording, automatic close from fills, trade review creation, and lifecycle event recording.
It records demo entry and exit fills, creates a manual review, and prints a compact final state summary.

## What Comes Next (Post-MVP)

Future work should remain incremental and preserve the domain boundaries established in Milestone 1.

Likely next areas:

- durable persistence with migrations and repository implementations
- an `OrderIntent` layer between plans and execution facts
- read-only market data context
- basic P&L computation after fill state is stable
- broker integration as an infrastructure adapter, not a source of trade meaning
- improved review and learning workflows

Detailed designs for those areas belong in future issues and ADRs.

## Status

Milestone 1 is complete as an MVP vertical slice.

Completed Milestone 1 work so far:

- initial Python project scaffold
- planned trade workflow skeleton
- open-position workflow from approved trade plan
- manual fill recording for open positions
- automatic position close when fills reduce open quantity to zero
- manual trade review for completed positions

Current focus:

- keep the first vertical slice narrow and correct
- preserve domain boundaries
- add persistence behavior only through infrastructure adapters
