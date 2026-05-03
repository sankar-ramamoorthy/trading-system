---
title: Broker Execution Boundary
status: accepted
date: 2026-05-03
tags: [adr, broker, paper-trading, execution, milestone-11]
---

# ADR-011: Broker Execution Boundary

## Status

Accepted

## Context

The system has local records for trade ideas, theses, plans, positions, order intents, manual fills, reviews, market context, and local secrets. The next execution step needs a broker boundary without allowing live, real-money order placement or autonomous trading behavior.

Broker data is an external execution fact. Local JSON remains the source of truth for internal trade records, lifecycle audit, reviews, and decision history.

## Decision

Milestone 11 accepts a provider-agnostic broker port and a simulated paper broker adapter for CLI and core-service workflows only.

The local domain adds `BrokerOrder` as the audit record connecting one `OrderIntent` to one broker submission. A broker-imported `Fill` may link back to both `order_intent_id` and `broker_order_id`.

Paper order submission requires:

- an existing non-canceled `OrderIntent`
- an existing open local `Position`
- matching `trade_plan_id` between the order intent and position
- no prior broker order for that order intent

The simulated adapter performs no external network calls. Sync requires an explicit simulated fill price so tests, demos, and operator actions remain intentional.

Future Alpaca paper integration should use a vault-first, environment-fallback credential resolver. The reserved secret names are:

- `ALPACA_API_KEY`
- `ALPACA_SECRET_KEY`

## Not Allowed

Milestone 11 does not add:

- real-money execution
- live Alpaca order submission
- autonomous trading
- trade recommendations
- full order-management-system behavior
- FastAPI broker controls
- React broker controls

## Rationale

A narrow broker boundary lets the system prove execution import, audit, and idempotence before any live broker API call exists.

Keeping the broker port provider-agnostic avoids coupling local domain records to Alpaca-specific models. Requiring a local position before broker fill import keeps the local lifecycle explicit and avoids broker data becoming the owner of internal position state.

## Consequences

Broker-submitted fills become local facts only after a human-controlled sync action. Imported fills use `source = "broker:simulated"` for this milestone.

The current implementation is intentionally paper-only. Later Alpaca work can map provider order status into the same `BrokerOrder` and `Fill` records while preserving the local audit boundary.
