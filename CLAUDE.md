# CLAUDE.md — trading-system Application Repo

This file tells Claude Code how to work in this repository.
Read this before writing any code or making any change.

---

## What This Repo Is

This is the **runtime application** for a professional-grade personal trading system.
It is a structured, auditable, CLI-driven trading workflow tool for a single discretionary trader.

This is NOT:
- a trading bot
- an automated execution engine
- a black-box system

---

## Current Milestone

**Milestone 6 — Read-only market data provider integration**

Active slice: Milestone 6C Issue 2 — narrow Massive.com daily bars adapter behind the provider registry.

Check `STATUS.md` for the current slice before starting any work.

---

## Before Writing Any Code

1. Read `STATUS.md` — confirm the active slice and constraints
2. Read `DOCS/domain-model.md` — the canonical source of truth for all entities
3. Read the relevant `DOCS/ADR/` entries for the area you are touching
4. Confirm there is an explicit issue or milestone slice justifying the work
5. Check the external knowledge base for design rationale if uncertain:
   ```
   C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
   ```

**No code without an explicit issue to tie it to.**

---

## Architecture

Modular monolith. `src/` layout:

```
src/trading_system/
    app/           # CLI entrypoints (Typer)
    domain/        # Business entities and domain logic — NO external dependencies
    services/      # Use-case orchestration
    rules_engine/  # Deterministic rule evaluation only
    ports/         # Repository interfaces and unit of work
    infrastructure/ # Persistence and external adapters
```

### Hard Boundary Rules

| Module | Rule |
|---|---|
| `domain/` | Must NOT import SQLAlchemy, CLI libs, or any external system |
| `services/` | Orchestrates workflows — not persistence details |
| `infrastructure/` | Only place for SQLAlchemy, provider adapters, file I/O |
| `rules_engine/` | Rule logic only — deterministic, no side effects |

---

## Domain Model — Do Not Collapse

These entities are canonical and must remain distinct:

- `TradeIdea`
- `TradeThesis`
- `TradePlan`
- `Position`
- `OrderIntent`
- `BrokerOrder`
- `Fill`
- `RuleEvaluation`
- `Violation`
- `TradeReview`
- `MarketContextSnapshot`
- `LifecycleEvent`

**A `Position` must originate from a `TradePlan`, never directly from a `TradeIdea`.**

---

## Active Constraints

- No broker integration
- No automated execution
- No live market data streaming
- No AI or ML decision-making
- JSON persistence is the active local backend
- Postgres is deferred
- External market data is read-only, advisory, and non-canonical
- Provider response objects and schemas must NOT enter domain logic
- `yfinance` is prototype-grade only — treat it that way
- `MarketContextSnapshot` is the storage boundary for all external provider data

---

## Provider Registry Pattern (Milestone 6)

Market data providers are resolved through a provider registry, not constructed directly in the CLI.

```
CLI --provider flag
    -> provider registry lookup
    -> provider adapter
    -> MarketContextSnapshot
    -> domain store
```

Adding a new provider means adding a new adapter behind the registry.
Do not bypass the registry. Do not couple provider schemas to domain entities.

---

## Coding Rules

- Prefer simple, explicit implementations
- No premature abstraction
- No `utils/` or `shared/` dumping-ground modules
- No generic plugin systems or unnecessary base classes
- Use UUIDs for entity identity
- Keep domain models and persistence models separate
- Add docstrings explaining module and class intent
- Rules must be deterministic, explicit, and auditable — no DSL yet

---

## Testing

Run the full suite before considering any slice complete:

```powershell
uv run pytest
```

Priorities:
- domain invariants
- rule evaluation behavior
- lifecycle transitions
- provider boundary protection
- source-of-truth boundaries

Record focused validation counts and full-suite counts in `STATUS.md` when closing a slice.

---

## CLI

Interface is Typer-based CLI only for now.

```powershell
uv run trading-system --help
uv run trading-system version
uv run trading-system demo-planned-trade
```

FastAPI is deferred until after Milestone 6 is closed (ADR-008).

---

## Persistence

Active backend: local JSON store at `.trading-system/store.json`
Configure via: `TRADING_SYSTEM_STORE_PATH`

Postgres + SQLAlchemy + Alembic are the intended production path but are deferred.
Do not introduce Postgres work during Milestone 6.

---

## Authoritative Documents

| Document | Role |
|---|---|
| `DOCS/domain-model.md` | Canonical entity and relationship definitions |
| `DOCS/systems-blueprint.md` | Architecture reference |
| `DOCS/ADR/` | Versioned architectural decisions |
| `STATUS.md` | Current implementation state |
| `README.md` | Workflow guide and CLI reference |
| `DOCS/milestone-6-market-data-provider-design.md` | Milestone 6 design |
| `DOCS/ADR/007-market-data-provider-boundary.md` | Provider boundary decision |
| `DOCS/ADR/009-massive-provider-boundary.md` | Massive.com provider decision |

---

## Commit and PR Rules

- Clear imperative messages: `Add Massive.com daily bars adapter`
- PR must include: summary, affected modules, linked issue or slice, validation notes
- Architecture changes must update `DOCS/` or `DOCS/ADR/`
- Update `STATUS.md` when a slice completes

---

## Relationship to AGENTS.md and the Knowledge Base

`AGENTS.md` contains durable repository rules shared with Codex.
`CLAUDE.md` (this file) contains Claude Code-specific operating instructions.
When they conflict on Claude Code behavior, prefer `CLAUDE.md`.

Design rationale, open questions, and synthesis live in the external knowledge base:

```
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

Do not duplicate that material here. Link to it when relevant.
