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

High-level layers:

- Deterministic Control Layer
- Market & Context Observation Layer
- Context Intelligence Layer
- Decision Support Layer

See:

- `doc/adr/001-system-architecture.md`
- `doc/adr/002-rules-vs-context.md`
- `doc/adr/003-development-and-deployment-strategy.md`
- `doc/adr/004-canonical-domain-and-source-of-truth.md`
- `doc/system-blueprint.md`

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

## Status

Early design and domain-definition phase.

Current priorities:

- define canonical entities  - i think done
- define schemas and source-of-truth boundaries - i think done
- translate architecture into executable issues and milestones - i think done
- Sync Knowledge Base: Initialize canonical entity pages in the Wiki based on DOCS/ADR-004. - I think Done
