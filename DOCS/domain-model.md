---

title: Formal Domain Model
version: v2
date: 2026-04-19
tags: [domain-model, architecture, entities, trading-system]
------------------------------------------------------------

# Overview

This document defines the canonical domain model for `trading-system`.

It establishes:

* core business entities
* boundaries between related concepts
* ownership and source-of-truth responsibilities
* a stable conceptual foundation for implementation

This is a **business/domain model**, not a database schema or API contract.

---

# Domain Modeling Principles

## 1. The system owns meaning

External systems provide facts.

The system defines:

* trade intent
* purpose
* thesis
* plans
* lifecycle state
* rule applicability
* review outcomes

---

## 2. Similar things must not be collapsed

The following are intentionally distinct:

* Instrument
* TradeIdea
* TradeThesis
* TradePlan
* Position
* OrderIntent
* BrokerOrder
* Fill
* ContextEvent
* TradeReview

---

## 3. The model must preserve time

The system must answer:

* what did I believe at entry?
* what changed later?
* when did thesis weaken?
* when did violations occur?

This requires revision-aware modeling.

---

## 4. Structured discretion

The system supports:

* deterministic rules
* contextual interpretation
* discretionary planning
* evolving state
* post-trade learning

---

# Domain Areas

1. Market Identity
2. Opportunity and Planning
3. Position and Execution
4. Rules and Discipline
5. Context and Monitoring
6. Journaling and Review
7. Revision and Lifecycle
8. Reconciliation and External Mapping

---

# Core Relationships

## Opportunity → Execution

```text
Instrument
   |
   v
TradeIdea -----> Playbook
   |
   +-----> TradeThesis (1..n over time)
   |
   +-----> TradePlan   (1..n over time)
   |
   v
Position -----> PositionLot
   |
   +-----> OrderIntent
   |
   +-----> BrokerOrder
               |
               v
              Fill
```

### Principle

A `Position` must originate from a `TradePlan`, not directly from a `TradeIdea`.

---

# 1. Market Identity

## Entities

* Instrument
* OptionContract
* Universe
* UniverseMembership

## Instrument

Canonical tradable identity.

## OptionContract

Option metadata linked to underlying instrument.

## Universe / UniverseMembership

Logical grouping and time-aware inclusion of instruments.

---

# 2. Opportunity and Planning

## Entities

* Playbook
* TradeIdea
* TradeThesis
* TradePlan
* WatchlistItem

## TradeIdea

Defines *what the trade is*.

* instrument
* playbook
* purpose
* direction
* horizon
* status

## TradeThesis

Defines *why the trade exists*.

* reasoning
* supporting evidence
* risks
* disconfirming signals

## TradePlan

Defines *how the trade will be executed*.

* entry criteria
* invalidation
* targets
* risk model
* sizing assumptions

---

# 3. Position and Execution

## Entities

* Position
* PositionLot
* OrderIntent
* BrokerOrder
* Fill
* BrokerAccount

## Position

System’s interpretation of an actual holding.

* linked_trade_plan (primary)
* linked_trade_idea (derived)
* instrument
* account
* purpose
* lifecycle state

## OrderIntent

Planned action before execution.

## BrokerOrder / Fill

External facts.

---

# 4. Rules and Discipline

## Entities

* Rule
* RuleEvaluation
* Violation

Rules are:

* explicit
* deterministic
* auditable

---

# 5. Context and Monitoring

## Entities

* ContextEvent
* ContextLink
* ThesisAssessment
* RegimeAssessment

Context is:

* observational
* structured
* advisory

---

# 6. Journaling and Review

## Entities

* JournalEntry
* TradeReview

---

# 7. Revision and Lifecycle

## Entities

* RevisionLog
* LifecycleEvent

All meaningful changes must be recorded.

---

# 8. Reconciliation and External Mapping

## Entities

* ExternalMapping
* ReconciliationRun
* ReconciliationIssue

---

# Source of Truth

## System owns

* ideas
* thesis
* plans
* lifecycle
* rules
* evaluations
* reviews

## External systems own

* orders
* fills
* balances
* market data
* news and filings

---

# Invariants

1. No position without meaning
2. Thesis ≠ Plan
3. External facts do not override internal meaning
4. Meaning-bearing objects require revision history
5. Context does not bypass rules

---

# V1 Implementation Scope

Initial vertical slice:

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

---

# Final Principle

The system must answer:

**What is this? Why does it exist? What changed? Was the process correct?**

---
