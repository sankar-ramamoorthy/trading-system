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
- `DOCS/domain-model.md`
- `DOCS/systems-blueprint.md`

## Current Workflow

Milestone 1 is implementing the first thin vertical slice:

```text
TradeIdea -> TradeThesis -> TradePlan -> plan approval -> RuleEvaluation -> Position -> LifecycleEvent
```

Implemented local workflows currently support:

- creating a `TradeIdea`
- creating a `TradeThesis` linked to the idea
- creating a `TradePlan` linked to the idea and thesis
- approving a `TradePlan`
- evaluating deterministic rules for an approved plan
- opening a `Position` from an approved plan
- recording a `POSITION_OPENED` lifecycle event

The position workflow preserves the canonical rule that a `Position` originates from a `TradePlan`, not directly from a `TradeIdea`. Position `instrument_id` and `purpose` are derived from the linked idea through the approved plan.

## Out of Scope Right Now

The current implementation intentionally does not include:

- broker integration
- market data ingestion
- AI or ML features
- reconciliation workflows
- FastAPI
- fills beyond the scaffolded manual fill entity
- trade review workflow implementation

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

Run the local planned-trade demo:

```powershell
uv run trading-system demo-planned-trade
```

The demo uses in-memory repositories and exercises the local workflow through plan approval, rule evaluation, position opening, and lifecycle event recording.

## Status

The repository has moved from design into initial implementation.

Completed Milestone 1 work so far:

- initial Python project scaffold
- planned trade workflow skeleton
- open-position workflow from approved trade plan

Current focus:

- keep the first vertical slice narrow and correct
- preserve domain boundaries
- add persistence behavior only through infrastructure adapters
