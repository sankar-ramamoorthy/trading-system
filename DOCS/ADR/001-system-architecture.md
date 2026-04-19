
---
id: ADR-001
title: Modular Monolith with Layered Intelligence Architecture
status: accepted
date: 2026-04-18
deciders: [owner]
tags: [architecture, core, foundational]
---

# Context

We are building a **professional-grade personal trading system** with the following goals:

- Enforce discipline and structured decision-making
- Support discretionary trading with rich context
- Integrate multiple data sources and brokers
- Evolve over time without architectural rewrites
- Avoid premature complexity and over-engineering

Key tensions:

- Flexibility vs structure
- Determinism vs contextual interpretation
- Simplicity vs long-term extensibility

We explicitly want to avoid:

- Rigid rule-only trading systems
- Black-box AI-driven decision systems
- Premature microservices architecture

---

# Decision

We will adopt a **Modular Monolith with Layered Intelligence Architecture**.

## Structural Choice

- Single codebase (modular monolith)
- Strong internal module boundaries
- Explicit domain model
- Adapters at system edges (data, broker, external tools)

## Intelligence Layers

The system is divided into four logical layers:

```

+--------------------------------------+
|         Decision Support Layer       |
+--------------------------------------+
|      Context Intelligence Layer      |
+--------------------------------------+
|   Market & Context Observation Layer |
+--------------------------------------+
|     Deterministic Control Layer      |
+--------------------------------------+

```

### Deterministic Control Layer
- Rules engine
- Risk constraints
- Trade lifecycle enforcement

### Observation Layer
- Market data ingestion
- Filings/news ingestion
- Peer/macro monitoring

### Context Intelligence Layer
- Thesis monitoring
- Regime detection
- Context summarization
- Change detection

### Decision Support Layer
- Trade evaluation outputs
- Alerts and recommendations
- Review prioritization

---

# Rationale

## Why Modular Monolith?

- Easier to reason about than distributed systems
- Lower operational overhead
- Faster iteration during early phases
- Can evolve into services later if needed

## Why Layered Intelligence?

Separates:
- What must be enforced (rules)
- What must be observed (data)
- What must be interpreted (context)
- What must be decided (human/system)

This prevents:
- AI from becoming unbounded decision authority
- Rules from trying to encode subjective nuance

## Why Not Microservices?

- No scaling requirement at this stage
- Adds operational complexity
- Increases cognitive load unnecessarily

---

# Consequences

## Positive

- Clean separation of concerns
- High evolvability
- Supports discretionary + systematic hybrid approach
- Enables AI without surrendering control
- Easier debugging and auditability

## Negative

- Requires discipline in module boundaries
- Some components (context layer) will evolve iteratively
- Potential refactoring needed if scaling beyond personal use

---

# Alternatives Considered

## 1. Fully Rule-Based System
Rejected:
- Cannot capture nuanced context
- Too brittle for real-world trading

## 2. AI-First System
Rejected:
- Poor auditability
- Hard to trust
- High risk of “intelligent nonsense”

## 3. Microservices Architecture
Rejected:
- Premature complexity
- Operational overhead unjustified

---

# Follow-ups

- Define module boundaries explicitly (see blueprint)
- Define canonical domain model (critical)
- Introduce event logging for traceability

