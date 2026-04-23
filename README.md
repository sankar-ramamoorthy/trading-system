---

````md
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
  - intent (TradePlan)  
  - execution (Fill)  
  - outcome (Position)  
  - reflection (TradeReview)

- **Canonical domain model**  
  The system owns trade meaning. External systems will only provide facts.

- **Incremental evolution**  
  Start simple. Expand only when justified.

---

## Architecture

The system follows a **modular monolith** architecture:

```text
src/trading_system/
````

Modules:

* `app/` — CLI entrypoints
* `domain/` — business logic and entities
* `services/` — use-case orchestration
* `rules_engine/` — deterministic rule evaluation
* `ports/` — interfaces (repositories, UoW)
* `infrastructure/` — persistence and adapters

See:

* `DOCS/ADR/001-system-architecture.md`
* `DOCS/ADR/002-rules-vs-context.md`
* `DOCS/ADR/003-development-and-deployment-strategy.md`
* `DOCS/ADR/004-canonical-domain-and-source-of-truth.md`
* `DOCS/ADR/005-mvp-definition-and-boundaries.md`
* `DOCS/domain-model.md`
* `DOCS/milestone-1-summary.md`
* `DOCS/milestone-2-roadmap.md`

---

## Core Workflow

```text
TradeIdea → TradeThesis → TradePlan → plan approval → RuleEvaluation → Position → Fill → Position close → TradeReview
```

`LifecycleEvent` records auditable state transitions throughout the lifecycle.

---

## How to Use This System (Milestone 1)

Milestone 1 provides a **CLI-driven, manual trading workflow**.

### Typical Flow

1. Define the trade:

   * Create `TradeIdea`
   * Create `TradeThesis`
   * Create `TradePlan`

2. Validate discipline:

   * Approve the plan
   * Run rule evaluation

3. Execute manually:

   * Open a `Position`
   * Record `Fill` entries as trades execute

4. Let the system track state:

   * Position updates automatically from fills
   * Position closes automatically when quantity reaches zero

5. Review the trade:

   * Create a `TradeReview` after closure

---

### Run the Demo

```powershell
uv run trading-system demo-planned-trade
```

This runs the full lifecycle:

> plan → approval → rules → position → fills → close → review

The demo now uses local JSON persistence. By default it writes to:

```text
.trading-system/store.json
```

Set `TRADING_SYSTEM_STORE_PATH` to use a different local file.

---

### Important Notes

* Execution is **manual**
* Prices and fills are **user-entered**
* No broker or market data integration exists yet
* The system is currently a **discipline and journaling tool**

---

## What is the MVP?

The MVP (Minimum Viable Product) is:

> A local, CLI-driven trading system that enforces structured trade intent, captures execution via manual fills, and supports post-trade review with full auditability.

### MVP Includes

* structured trade definition (idea → thesis → plan)
* deterministic rule evaluation
* position creation from approved plans
* manual fill recording
* automatic position state tracking
* automatic position closure
* one structured trade review per position
* lifecycle audit trail

---

### MVP Does NOT Include

* broker integration
* automated execution
* market data feeds
* P&L analytics
* dashboards or UI
* AI-generated insights

The MVP focuses on:

> **discipline, structure, and auditability — not automation**

---

## Current Capabilities (Milestone 1)

* trade idea → thesis → plan workflow
* plan approval and rule validation
* position opening from approved plan
* manual fill recording
* execution state tracking
* automatic position closure
* lifecycle event audit trail
* one immutable trade review per position
* CLI demo covering full lifecycle

---

## What Comes Next (Post-MVP)

Future work will extend the system incrementally.

### Planned Areas

1. **Persistence**

   * local JSON persistence first; SQLite/Postgres remain later options

2. **OrderIntent**

   * bridge between plan and fills

3. **Basic P&L**

   * realized P&L from fills

4. **Querying**

   * list and inspect past trades

5. **Market Data (read-only)**

   * contextual price information

6. **Broker Integration (later)**

   * adapter only, not source of truth

7. **Review Enhancements**

   * tagging, filtering, learning

---

### Still Out of Scope

* real-time trading systems
* automated strategies
* dashboards
* AI decision engines

---

## Development Approach

* no code without an explicit issue
* milestone-driven development
* domain-first design
* strict boundary enforcement
* simple implementations over flexible abstractions

---

## Local Development

This project uses `uv`.

### Run tests

```powershell
uv run pytest
```

### Run CLI

```powershell
uv run trading-system version
```

### Run demo

```powershell
uv run trading-system demo-planned-trade
```

### Inspect persisted positions

```powershell
uv run trading-system list-positions
uv run trading-system list-positions --state closed
uv run trading-system show-position <position-id>
uv run trading-system show-position-timeline <position-id>
```

---

## Knowledge Base

This project uses a split knowledge model:

### Repository (source of truth for code)

* `DOCS/ADR/` — architectural decisions
* `DOCS/` — domain and system documentation

### External Knowledge Base (long-term memory)

Located at:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

Contains:

* canonical entity definitions
* trading rules and concepts
* cross-topic synthesis

---

## Status

Milestone 1 is complete.

The system supports:

> intent → execution → closure → review

Current focus:

* maintaining domain clarity
* preparing for persistence and OrderIntent (Milestone 2)

---

## Final Note

This system is built to enforce **thinking quality**, not just track trades.

If it feels “manual,” that is intentional.

Automation will come later — on top of a correct foundation.

```

---

