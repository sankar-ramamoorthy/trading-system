---
title: Post-Milestone 11 Roadmap
status: draft
date: 2026-05-03
tags: [roadmap, broker, paper-trading, trading-system]
---

# Post-Milestone 11 Roadmap

Milestone 11 closed the first broker execution boundary with simulated paper execution through core services and CLI commands only. Milestones 12 through 16 completed the first paper-trading hardening, Alpaca broker adapter, broker reconciliation, Alpaca market data, and Finqual fundamentals layers. The next accepted sequence expands broker visibility before browser execution controls.

The guiding rule remains:

```text
Broker data is external execution fact.
Local trade records remain the system source of truth.
```

## Recommended Next Milestones

### Milestone 12: Paper Execution Hardening

Status: complete. See `DOCS/milestone-12-issue-map.md`.

Make the current simulated paper workflow easier to inspect, safer to operate, and harder to misuse.

Recommended direction:

- add broker-order list and inspection workflows
- surface broker-order links more clearly in plan, position, and timeline views
- improve audit visibility for submitted, filled, canceled, rejected, and repeated sync cases
- add simulated cancellation or rejection only if needed to test lifecycle behavior
- keep scope core services and CLI only

Do not add Alpaca, FastAPI broker endpoints, React broker controls, real-money execution, autonomous trading, or recommendations.

### Milestone 13: Alpaca Paper Adapter

Add live Alpaca paper-trading integration behind the accepted broker port.

Recommended direction:

- implement Alpaca paper adapter behind `BrokerClient`
- use vault-first, environment-fallback resolution for `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- submit only from existing approved local `OrderIntent` records and open local `Position` records
- map Alpaca order status into local `BrokerOrder` records
- import broker fills into local `Fill` records without making broker positions canonical
- keep controls CLI-only for the first Alpaca slice

Do not add real-money execution, browser execution controls, autonomous trading, or full order-management-system behavior.

### Milestone 14: Broker Reconciliation And Status Sync

Handle local-vs-broker mismatches explicitly after a real paper broker exists.

Recommended direction:

- add explicit sync and reconciliation commands
- detect broker-order status changes without silently redefining trade meaning
- report local-vs-broker mismatches clearly
- preserve idempotent fill import
- record audit events for sync results and mismatches

Broker-reported positions must remain external facts, not canonical local positions.

### Milestone 15: Alpaca Read-Only Market Data Provider

Status: complete. See `DOCS/milestone-15-issue-map.md`.

Add Alpaca as a read-only market and options data provider behind the existing market-context boundary.

Completed direction:

- add `fetch-market-data --provider alpaca`
- add `fetch-options-chain --provider alpaca`
- use vault-first, environment-fallback resolution for `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- store output only as `MarketContextSnapshot`
- keep Alpaca data-provider code separate from Alpaca broker execution code

Do not add broker execution, automatic provider fallback, live streaming, scheduled refresh, recommendations, AI interpretation, or trade mutation.

### Milestone 16: Finqual Fundamentals Provider

Status: complete. See `DOCS/milestone-16-issue-map.md`.

Introduce Finqual as a read-only fundamentals and ownership provider candidate.

Completed direction:

- use vault-first, environment-fallback resolution for `FINQUAL_API_KEY`
- add `fetch-financial-statement --provider finqual`
- add `fetch-insider-transactions --provider finqual`
- add `fetch-13f --provider finqual`
- store all output only as `MarketContextSnapshot`
- keep Finqual advisory and non-canonical

Do not add automatic provider fallback, automated scoring, recommendations, AI interpretation, portfolio analytics, or trade mutation.

### Milestone 17: API/Web Broker Visibility

Expose broker-order status to the local web product without browser execution controls.

Recommended direction:

- add read-only FastAPI broker-order endpoints
- show broker-order status and linked fills in web plan and position views
- keep submission, sync, cancel, and rejection actions out of the browser

This milestone is visibility only. Execution controls remain CLI-only.

### Milestone 18: Browser Paper Execution Controls

Add human-controlled browser paper execution only after CLI and read-only web visibility are stable.

Recommended direction:

- add explicit submit and sync controls in the browser
- require confirmation before paper submission
- display linked order intent, position, provider, side, quantity, order type, and prices before submit
- keep real-money execution blocked

Browser controls must remain paper-only and human-invoked.

## Deferred Decisions

The following were intentionally deferred by Milestone 11:

- live Alpaca paper submission: Milestone 13
- read-only Alpaca market/options data: Milestone 15
- Finqual fundamentals and ownership context: Milestone 16
- FastAPI broker visibility: Milestone 17 or later
- React broker controls: Milestone 18 or later
- real-money trading: readiness gate, not a normal near-term milestone
- autonomous trading: out of scope
- generated recommendations or AI execution instructions: out of scope
- full OMS behavior: out of scope unless a later ADR changes the boundary

## Real-Money Readiness Gate

Real-money execution should not be scheduled as the next ordinary milestone. It requires explicit evidence first:

- stable paper trading behavior
- clean local records
- consistent review discipline
- known playbook and invalidation quality
- useful reconciliation behavior
- accepted ADR for real-money execution boundaries and failure modes

Until that gate is met, broker work remains paper-only and human-controlled.
