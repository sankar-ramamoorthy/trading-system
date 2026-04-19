---
id: ADR-004
title: Canonical Domain Model and Source-of-Truth Boundaries
status: accepted
date: 2026-04-18
deciders: [owner]
tags: [domain, data, architecture, core, integrity]
---

# Context

The system integrates multiple external sources:

- Market data providers
- Broker platforms (e.g., Alpaca, thinkorswim/Schwab)
- Charting/alert platforms (e.g., TradingView)
- Manual user input

Each of these systems:
- uses its own schema
- may have inconsistencies
- may be incomplete or delayed
- may change over time

Without a clear definition of **source of truth**, the system risks:

- inconsistent state
- mismatched positions vs intent
- corrupted trade history
- unreliable analytics
- loss of auditability

This is especially critical because the system’s primary goal is:

> enforce discipline and maintain accurate trade context over time

---

# Decision

We will define:

## 1. A Canonical Internal Domain Model

All external data must be:
- ingested
- normalized
- mapped

into internal domain entities.

External schemas are never used directly outside adapter boundaries.

---

## 2. Explicit Source-of-Truth Ownership by Domain

Different parts of the system will have clearly defined ownership.

### System is the source of truth for:

- Trade ideas and plans
- Trade intent (why a position exists)
- Playbooks and strategy classification
- Rules and rule evaluations
- Position purpose (investment / swing / tactical)
- Trade lifecycle state
- Thesis and thesis revisions
- Journal entries and reviews
- Rule violations and overrides

---

### Broker is the source of truth for:

- Executed orders
- Fill details
- Account balances
- Raw position quantities (as reported)

---

### Market data providers are the source of truth for:

- price and volume data (with caveats)
- options chains and contract metadata
- historical bars (subject to quality differences)

---

### Context sources are the source of truth for:

- filings
- news events
- macro events
- peer activity

But not for interpretation.

---

# Ownership Model


+----------------------------+
|   External Systems         |
| (broker, data, context)    |
+-------------+--------------+
|
v
+----------------------------+
|   Adapters / Ingestion     |
|  (translation layer)       |
+-------------+--------------+
|
v
+----------------------------+
|   Canonical Domain Model   |
|   (system source of truth) |
+----------------------------+
|
v
+----------------------------+
|  Rules / Context / Decision|
+----------------------------+


---

# Rationale

## Why canonical model?

Because:

- external APIs change
- multiple providers may be used
- schemas are inconsistent
- we need a stable internal representation

Without this, the system becomes tightly coupled to vendors.

---

## Why explicit source-of-truth boundaries?

Because different data answers different questions:

| Question                          | Source |
|----------------------------------|--------|
| What did I intend?               | System |
| What actually executed?          | Broker |
| What is the market doing?        | Data provider |
| What changed externally?         | Context sources |

Mixing these leads to confusion and incorrect conclusions.

---

# Key Principle

> The system owns meaning. External systems provide facts.

---

# Reconciliation Strategy

Because multiple sources exist, reconciliation is required.

## Position reconciliation

Compare:
- broker-reported positions
- system-tracked positions

Detect:
- missing trades
- manual trades
- mismatched quantities
- stale internal state

---

## Trade linkage

All fills must be:

- linked to a TradeIdea, OR
- explicitly marked as **unplanned**

Unlinked trades are treated as:
- violations
- or requiring classification

---

## Event reconciliation

Context events must be:

- timestamped
- attributable to a source
- comparable across time

---

# Invariants

The system must enforce:

## 1. No position without intent

Every position must:
- link to a TradeIdea, OR
- be explicitly classified as unplanned

---

## 2. No silent state mutation

Changes to:
- thesis
- rules
- trade plans

must be recorded as revisions.

---

## 3. External data must not overwrite internal meaning

Example:

Broker says:
- position exists

System must still determine:
- why it exists
- what type of position it is
- whether it is valid

---

## 4. Internal state must survive external inconsistency

If:
- data feed is delayed
- broker temporarily mismatches

System must:
- detect inconsistency
- not silently corrupt internal state

---

# Consequences

## Positive

- strong data integrity
- clear audit trail
- reliable analytics
- clean separation of concerns
- easier integration of new providers
- supports long-term system evolution

---

## Negative

- requires explicit mapping layers
- adds upfront design effort
- reconciliation logic must be implemented
- cannot rely on external systems “as-is”

---

# Anti-Patterns to Avoid

- using broker position data as trade definition
- directly using API response objects in domain logic
- mutating trade intent based on external updates
- assuming data provider correctness
- allowing orphan trades to persist

---

# Example

## Bad

- Broker shows 100 shares of AAPL
- System assumes this is a swing trade

## Good

- Broker shows 100 shares of AAPL
- System links to TradeIdea #42
- TradeIdea defines:
  - swing playbook
  - thesis
  - timeframe
- System evaluates if position is still valid

---

# Follow-ups

- Define canonical entity schemas (TradeIdea, Position, etc.)
- Define adapter interfaces
- Implement reconciliation module
- Define event logging strategy
- Define revision tracking for key objects

---

# 🧠 Why this ADR matters so much

This is the one that prevents:

* “my broker says X but my system says Y”
* “I don’t know why I’m in this trade”
* “this P&L analysis doesn’t make sense”
* “did I change my thesis or was it always like this?”

In other words:

👉 It protects **truth, memory, and accountability**

Which is exactly what your system is about.

---

# ✅ You now have a solid ADR foundation

You have:

* **ADR-001** → architecture style
* **ADR-002** → rules vs context
* **ADR-003** → dev/deploy strategy
* **ADR-004** → domain + truth model


---

