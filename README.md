---

# trading-system

A professional-grade personal trading system for structured discretionary trading.

---

## Purpose

This project is designed to help a single trader:

- manage trades with full context
- enforce discipline and process
- separate intent from execution
- capture execution reality
- review and improve decision-making over time

This is **not**:

- a trading bot
- a black-box system
- an automated execution engine

It is a **structured, auditable trading workflow system**.

---

## Core Principles

- **Structured trade representation**
  Every trade has intent, thesis, and a plan before execution.

- **Deterministic discipline**
  Hard rules are explicit, enforceable, and auditable.

- **Separation of concerns**
  - intent (`TradePlan`)
  - execution intent (`OrderIntent`)
  - execution fact (`Fill`)
  - outcome (`Position`)
  - reflection (`TradeReview`)

- **Canonical domain model**
  The system owns trade meaning. External systems only provide facts.

- **Incremental evolution**
  Start simple. Expand only when justified.

---

## Architecture

The system follows a **modular monolith** architecture:

```text
src/trading_system/
```

Modules:

- `app/` - CLI entrypoints
- `domain/` - business logic and entities
- `services/` - use-case orchestration
- `rules_engine/` - deterministic rule evaluation
- `ports/` - interfaces and persistence boundaries
- `infrastructure/` - persistence and adapters

See:

- `DOCS/ADR/001-system-architecture.md`
- `DOCS/ADR/002-rules-vs-context.md`
- `DOCS/ADR/003-development-and-deployment-strategy.md`
- `DOCS/ADR/004-canonical-domain-and-source-of-truth.md`
- `DOCS/ADR/005-mvp-definition-and-boundaries.md`
- `DOCS/domain-model.md`
- `DOCS/milestone-1-summary.md`
- `DOCS/milestone-2-roadmap.md`
- `DOCS/milestones-3-to-5-roadmap.md`
- `DOCS/milestone-4-market-context-design.md`
- `DOCS/milestone-5-review-learning-and-local-ops-design.md`

---

## Core Workflow

```text
TradeIdea -> TradeThesis -> TradePlan -> plan approval -> RuleEvaluation -> OrderIntent -> Position -> Fill -> Position close -> TradeReview
```

`LifecycleEvent` records auditable state transitions throughout the lifecycle.

---

## How To Use This System

The current repository provides a CLI-driven, manual trading workflow built on the completed Milestone 1 MVP and extended by Milestone 2 implementation work.

### Typical Flow

1. Define the trade:
   - create `TradeIdea`
   - create `TradeThesis`
   - create `TradePlan`
2. Validate discipline:
   - approve the plan
   - run rule evaluation
3. Execute manually:
   - create an `OrderIntent` from the approved plan
   - open a `Position`
   - record `Fill` entries as trades execute
4. Let the system track state:
   - position updates automatically from fills
   - position closes automatically when quantity reaches zero
   - realized P&L is derived on the read side for closed positions
5. Review the trade:
   - create a `TradeReview` after closure

### Run The Demo

```powershell
uv run trading-system demo-planned-trade
```

The demo uses local JSON persistence. By default it writes to:

```text
.trading-system/store.json
```

Set `TRADING_SYSTEM_STORE_PATH` to use a different local file.

### Core Write Workflow

```powershell
uv run trading-system create-trade-idea --instrument-id <instrument-id> --playbook-id <playbook-id> --purpose swing --direction long --horizon days_to_weeks
uv run trading-system create-trade-thesis <trade-idea-id> --reasoning "Setup has a catalyst."
uv run trading-system create-trade-plan --trade-idea-id <trade-idea-id> --trade-thesis-id <trade-thesis-id> --entry-criteria "Breakout confirmation." --invalidation "Close below setup low." --risk-model "Defined stop and max loss."
uv run trading-system approve-trade-plan <trade-plan-id>
uv run trading-system evaluate-trade-plan-rules <trade-plan-id>
uv run trading-system create-order-intent --trade-plan-id <trade-plan-id> --symbol AAPL --side buy --order-type limit --quantity 100 --limit-price 25.50
uv run trading-system open-position <trade-plan-id>
uv run trading-system record-fill --position-id <position-id> --side buy --quantity 100 --price 25.50 --order-intent-id <order-intent-id>
uv run trading-system record-fill --position-id <position-id> --side sell --quantity 100 --price 27.00
uv run trading-system create-trade-review --position-id <position-id> --summary "Followed the plan." --what-went-well "Entry was clean." --what-went-poorly "Exit could have been faster."
```

### Read And Inspect Stored Data

```powershell
uv run trading-system list-trade-ideas
uv run trading-system list-trade-plans
uv run trading-system show-trade-plan <trade-plan-id>
uv run trading-system list-trade-reviews
uv run trading-system show-trade-review <trade-review-id>
uv run trading-system list-positions
uv run trading-system list-positions --state closed
uv run trading-system show-position <position-id>
uv run trading-system show-position-timeline <position-id>
```

### Important Notes

- execution is manual
- prices and fills are user-entered
- data persists locally in JSON by default
- no broker or market data integration exists yet
- the system is currently a discipline and journaling tool

---

## MVP Boundary

Milestone 1 is the MVP boundary defined by ADR-005.

The MVP is:

> A local, CLI-driven trading system that enforces structured trade intent, captures execution via manual fills, and supports post-trade review with full auditability.

### MVP Includes

- structured trade definition (`TradeIdea -> TradeThesis -> TradePlan`)
- deterministic rule evaluation
- position creation from approved plans
- manual fill recording
- automatic position state tracking
- automatic position closure
- one structured trade review per position
- lifecycle audit trail

### MVP Does Not Include

- broker integration
- automated execution
- market data feeds
- advanced P&L analytics
- dashboards or UI
- AI-generated insights

The MVP focuses on disciplined, auditable workflow rather than automation.

---

## Current Capabilities

Milestone 1 is complete.

Milestone 2 is functionally complete in code and is awaiting explicit closeout and any final documentation polish.

Milestone 3 has started with manual-workflow usability improvements.

Current codebase capabilities include:

- durable local JSON persistence
- trade idea, thesis, and plan workflows
- plan approval and deterministic rule validation
- narrow `OrderIntent` support between approved plan and manual fill
- position opening from approved plans
- manual fill recording with optional `OrderIntent` linkage
- execution state tracking and automatic position closure
- basic realized P&L for closed positions on the read side
- lifecycle event audit trail and position timeline output
- explicit CLI write commands for the core workflow
- read-side CLI commands for trade ideas, trade plans, trade reviews, and positions
- consistent read-command presentation for headers, empty states, section ordering, and optional values

---

## What Comes Next

Future work should stay incremental and preserve the current domain boundaries.

The current milestone position is:

- Milestone 2: functionally complete, awaiting explicit closeout
- Milestone 3: started

The accepted near-term roadmap after Milestone 2 is:

- **Milestone 3: Manual Workflow Usability**
  Continue improving daily manual usage with CLI polish, chaining support, clearer summaries, and removal of avoidable friction.

- **Milestone 4: Read-Only Market Context**
  Add external market and context data as read-only support for planning and review without making it canonical trade meaning.

- **Milestone 5: Review, Learning, and Local Operations**
  Expand review tagging, filtering, reporting, export, and local operational robustness without turning the system into a portfolio engine.

See `DOCS/milestones-3-to-5-roadmap.md` for the canonical roadmap and the milestone design notes for Milestones 4 and 5.

Still explicitly deferred:

- Postgres as the active backend
- broker integration
- FastAPI
- reinforcement learning
- live automation
- dashboards
- AI decision engines

Reinforcement learning remains exploratory knowledge-base material, not the accepted Milestone 3 plan for this repository.

---

## Local Development

This project uses `uv`.

Run tests:

```powershell
uv run pytest
```

Run CLI:

```powershell
uv run trading-system version
uv run trading-system --help
```

---

## Knowledge Base

This project uses a split knowledge model.

Repository sources of truth:

- `DOCS/ADR/` for versioned architectural decisions
- `DOCS/` for domain and milestone documents

External knowledge base:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

It captures canonical entity notes, cross-topic synthesis, processed implementation notes, and exploratory future-direction documents.

---

## Status

Milestone 1 is complete.

Milestone 2 work already present in the repo includes:

- durable local JSON persistence
- retrieval, review inspection, and timeline commands
- narrow `OrderIntent`
- read-side realized P&L
- explicit CLI write commands
- practical read-side CLI inspection for ideas, plans, reviews, and positions

The currently implemented workflow is:

> intent -> order intent -> execution -> closure -> review

Current focus:

- maintaining domain clarity
- formally closing out Milestone 2 in docs and status framing
- continuing Milestone 3 manual-workflow usability improvements
- keeping later milestones scoped without weakening boundaries

---

## Final Note

This system is built to enforce thinking quality, not just track trades.

If it feels manual, that is intentional. Automation should only be added on top of a correct and auditable foundation.
