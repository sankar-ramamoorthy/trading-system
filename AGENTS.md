
---

# Repository Guidelines

## Project Status

This repository is transitioning from design into initial implementation.

Authoritative documents:

* `README.md`
* `DOCS/system-blueprint.md`
* `DOCS/domain-model.md`
* `DOCS/ADR/`

When conflicts exist, **domain-model.md is the canonical source of truth for entities and relationships**.

---

## Architecture Rules

This system is a **modular monolith**, not a microservices system.

Implementation must follow a `src/` layout:

```
src/trading_system/
```

Primary module structure:

* `app/` – CLI or API entrypoints
* `domain/` – core business entities and domain logic
* `services/` – use-case orchestration
* `rules_engine/` – deterministic rule evaluation
* `ports/` – interfaces (repositories, unit of work)
* `infrastructure/` – database, persistence, external adapters

### Strict Boundaries

* `domain/` must NOT depend on SQLAlchemy, CLI, or external systems
* `services/` orchestrates workflows, not persistence details
* `infrastructure/` implements persistence and external concerns
* `rules_engine/` contains rule logic only

---

## Domain Model Rules

Preserve canonical distinctions defined in `DOCS/domain-model.md`.

The following must NEVER be collapsed:

* `TradeIdea`
* `TradeThesis`
* `TradePlan`
* `Position`
* `OrderIntent`
* `BrokerOrder`
* `Fill`
* `RuleEvaluation`
* `Violation`
* `TradeReview`

Critical principle:

* A `Position` must originate from a `TradePlan`, not directly from a `TradeIdea`

---

## Implementation Scope (Current Phase)

The system is being built using a **thin vertical slice**.

Allowed entities for initial implementation:

* Instrument
* TradeIdea
* TradeThesis
* TradePlan
* Position
* Fill (manual)
* Rule
* RuleEvaluation
* Violation
* TradeReview
* LifecycleEvent

Explicitly defer:

* broker integration
* market data ingestion
* context ingestion
* AI or ML features
* reconciliation systems

---

## Scaffolding Rules

Code should normally only be created for an explicit issue or milestone.

Exception:

Scaffolding of the approved architecture is allowed when explicitly requested.

During scaffolding:

* create minimal, correct structure
* do NOT implement full business logic
* do NOT introduce unnecessary abstractions
* prefer simple stubs with clear intent

---

## Coding Guidelines

* Prefer simple, explicit implementations
* Avoid premature abstraction
* Add docstrings explaining intent of modules and classes
* Use UUIDs for entity identity (when implemented)
* Keep domain models and persistence models separate

Do NOT create:

* `utils/` or `shared/` dumping-ground modules
* generic frameworks or plugin systems
* unnecessary base classes or factories

---

## Rule Engine Guidelines

Rules must be:

* deterministic
* explicit
* auditable

Initial implementation should use simple Python classes.

Do NOT build a DSL or configuration-driven rule system yet.

---

## Data and Persistence

* Use Postgres for persistence
* Use SQLAlchemy in `infrastructure/` only
* Use Alembic for migrations
* Use JSONB where flexible structure is appropriate

---

## Interface Guidelines

Initial interface should be:

* CLI using Typer

Optional later:

* FastAPI (only after core workflow is stable)

---

## Testing Guidelines

When tests are introduced, prioritize:

* domain invariants
* rule evaluation behavior
* lifecycle transitions
* source-of-truth boundaries

---

## Useful Local Commands (PowerShell)

* `Get-ChildItem -Recurse -File`
  List all files

* `Select-String -Path *.md -Pattern "term" -Recurse`
  Search Markdown files

* `Get-ChildItem DOCS -Recurse -File | Select-String "TradeIdea"`
  Search domain terms

* `Get-Content path\to\file.md`
  Read file contents

---

## Commit and PR Guidelines

Use clear, imperative commit messages:

* `Add trade idea entity`
* `Implement rule evaluation skeleton`

Pull requests should include:

* summary
* affected modules
* linked issue or milestone
* validation notes

Architecture changes must update docs and/or ADRs.

---

## Agent-Specific Instructions

Agents must:

* follow AGENTS.md strictly
* prioritize correctness over completeness
* prefer simple implementations over abstraction
* avoid inventing new architecture
* Respect the project rule in README.md: no code without an explicit issue to tie it to.


Before coding, align with the external knowledge base at C:\Users\bosto\dockerstuff\knowledge-base\trading-system\ when available, especially its AGENTS.md and canonical entity notes.
External knowledge base :

```
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```
If uncertain, choose the simpler implementation consistent with existing rules.

---

## Final Principle

The system exists to enforce disciplined decision-making.

Every implementation choice should support:

* clarity of intent
* separation of concerns
* auditability
* long-term maintainability

---

