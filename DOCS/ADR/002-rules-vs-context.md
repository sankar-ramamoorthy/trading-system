---
id: ADR-002
title: Separation of Deterministic Rules and Contextual Intelligence
status: accepted
date: 2026-04-18
deciders: [owner]
tags: [rules, ai, discipline, trading]
---

# Context

Trading decisions involve two fundamentally different types of logic:

1. **Deterministic constraints**
2. **Contextual interpretation**

Most systems fail by:
- Over-relying on rigid rules (too brittle)
- Over-relying on intuition/AI (too unstructured)

We want a system that:
- Enforces discipline
- Understands nuance
- Remains auditable

---

# Decision

We will explicitly separate:

## 1. Deterministic Rules (Hard Constraints)

These are:

- Objective
- Enforceable
- Auditable
- Non-negotiable (unless explicitly overridden)

Examples:

- Max position size
- Earnings proximity restrictions
- Allowed playbooks
- Risk limits
- Holding period constraints
- Liquidity requirements

These are implemented in the **Rules Engine**.

---

## 2. Contextual Intelligence (Interpretive Signals)

These are:

- Subjective or probabilistic
- Informational, not authoritative
- Continuously evolving

Examples:

- Thesis weakening due to new filings
- Peer divergence
- Macro environment changes
- Chart structure degradation
- Market regime shifts

These are implemented in the **Context Intelligence Layer**.

---

## Interaction Model

```

```
       +------------------------+
       |   Context Intelligence |
       |  (Advisory Signals)    |
       +-----------+------------+
                   |
                   v
```

+----------------------+----------------------+
|          Decision Support Layer             |
+----------------------+----------------------+
^
|
+-----------+------------+
|   Rules Engine         |
| (Hard Constraints)     |
+------------------------+

```

---

# Rationale

## Why Separate?

Because these two domains behave differently:

| Aspect        | Rules                  | Context                  |
|--------------|------------------------|--------------------------|
| Nature        | Deterministic          | Interpretive             |
| Output        | Pass / Fail            | Gradual / Probabilistic  |
| Purpose       | Protect capital        | Improve judgment         |
| Failure Mode  | Too rigid              | Too vague                |

Mixing them leads to:
- fragile systems
- untraceable decisions
- inconsistent behavior

---

# Consequences

## Positive

- Clear mental model
- Strong discipline enforcement
- Flexible interpretation layer
- Enables AI safely
- Improves auditability

## Negative

- Requires explicit integration points
- Context signals must be structured carefully
- Some duplication in evaluation logic

---

# Anti-Patterns to Avoid

- Encoding subjective judgment as rigid rules
- Allowing AI to bypass rules
- Treating context signals as binary truth
- Ignoring context because it’s “not deterministic”

---

# Follow-ups

- Define rule schema and storage
- Define context assessment structure
- Define how context impacts decisions (without overriding rules)

