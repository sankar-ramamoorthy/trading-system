---
title: Product Roadmap
status: draft
date: 2026-04-26
tags: [roadmap, product, trading-system]
---

# Product Roadmap

This roadmap separates accepted near-term implementation work from longer-term product direction.

The current system remains a local-first, human-in-the-loop trading workflow. It should improve decision quality through structure, auditability, context, and review before any intelligence or automation work is considered.

## Roadmap Rules

- Near-term milestones describe implementation direction for this repository.
- Long-term versions describe product direction and readiness gates, not current implementation commitments.
- ADRs record durable boundaries; this roadmap records evolving sequencing.
- Learning systems must not be introduced before the system has reliable ground truth.

## Near-Term Roadmap

The accepted near-term sequence has advanced through Milestone 11. See `DOCS/post-milestone-11-roadmap.md` for the recommended Milestones 12 through 16 sequence.

### Milestone 3: Manual Workflow Usability

Status: complete.

Milestone 3 made the CLI workflow practical for repeated manual use while preserving the explicit trade lifecycle and audit boundary.

### Milestone 4: Read-Only Market Context

Status: complete.

Milestone 4 adds read-only market and context support for planning and review.

Allowed direction:

- selected read-only market or context inputs
- local snapshots or cached references for later review
- CLI inspection of context alongside planning and review
- clear separation between external context and internal trade meaning

Non-goals:

- live streaming market data
- broker coupling
- execution triggers
- automated plan creation
- external context becoming canonical trade meaning

### Milestone 5: Review, Learning, And Local Operations

Status: complete.

Milestone 5 deepens post-trade review and local operational robustness.

Allowed direction:

- review tagging and filtering
- narrow journal-grade summaries
- export workflows for local inspection or backup
- practical local backup and restore support

Non-goals:

- portfolio-engine behavior
- broad analytics platform work
- AI-generated review content
- reinforcement learning
- cloud-first operations

### Milestone 6: Read-Only Market Data Provider Integration

Status: complete.

Milestone 6 introduces the first external market data provider behind the accepted ADR-007 boundary. The first implementation slice is the `fetch-market-data` command for prototype-grade `yfinance` daily OHLCV snapshots.

Allowed direction:

- optional prototype-grade `yfinance` provider adapter
- daily OHLCV history as the first provider data shape
- explicit user-invoked fetches stored as `MarketContextSnapshot` records
- advisory, non-canonical market data for planning and review
- explicit provider selection with yfinance as the default provider and Massive.com as an additional implemented provider

Completed first implementation slice:

- `fetch-market-data` for user-invoked daily OHLCV snapshots
- explicit snapshot storage as `MarketContextSnapshot` records
- optional linking to trade-plan, position, or trade-review targets
- provider registry boundary and `--provider yfinance`
- narrow Massive.com daily bars adapter through `--provider massive`

Completed sequencing:

- Milestone 6A: prototype-grade `yfinance` daily OHLCV snapshot fetch is complete.
- Milestone 6B Issue 1: provider-boundary hardening is complete.
- Milestone 6C Issue 1: Massive.com provider boundary is accepted in ADR-009.
- Milestone 6C Issue 2: narrow Massive.com daily bars adapter is complete.
- Milestone 6D: Milestone 6 closeout is complete.
- ADR-008 API-first web product work continued in completed Milestone 7.

Non-goals:

- live streaming market data
- execution-grade quotes
- broker integration
- execution triggers
- provider-driven recommendations
- automatic trade, thesis, review, rule, or lifecycle mutation

### Milestone 7: API-First Trade Capture Workspace

Status: complete. See `DOCS/milestone-7-closeout.md`.

Milestone 7 delivered the first local web product: Docker Compose runtime, FastAPI trade-capture API, and React/Vite browser workspace for natural-language capture, parse, edit, and save of structured trade records. The CLI and web interface share the same local JSON store.

### Milestone 8: Options Chain Ingestion

Status: complete. See `DOCS/milestone-8-issue-map.md`.

Add options chain data as the first market data depth extension. Options context helps traders assess strike selection, implied volatility regime, and open interest before entering a position.

Allowed direction:

- `fetch-options-chain SYMBOL --expiry YYYY-MM-DD --provider yfinance|massive`
- yfinance options chain (calls + puts) for a single expiration date
- Massive.com options chain with greeks (delta, gamma, theta, vega) where available on the free tier
- Stored as `context_type: options_chain` MarketContextSnapshot, linkable to plans, positions, or reviews
- Symbol auto-resolves from ticker (same as `fetch-market-data`)

Non-goals:

- live options quotes or streaming
- options pricing models or greeks calculation
- options strategy construction or recommendation
- order execution of any kind
- multi-leg or complex positions

### Milestone 9: Web Product Beyond First Capture

Status: complete. See `DOCS/milestone-9-issue-map.md`.

Extend the browser interface beyond the initial trade-capture workflow to support daily use without the CLI.

Completed direction:

- list and detail views for saved plans with linked idea and thesis context
- plan approval from the browser
- context attachment from the browser by copying an existing market snapshot to a plan
- metadata-only context discovery in the browser

Non-goals:

- broker integration or execution
- automated trading or signals
- multi-user access or authentication
- rule evaluation before approval

### Milestone 10: Secure Credentials

Status: complete. See `DOCS/milestone-10-issue-map.md`.

Replace plain-text `.env` API key management with an encrypted local key vault for CLI use.

Completed direction:

- ADR for key vault boundary (library-first, provider-agnostic)
- `local_secret_vault` library using Fernet encryption and OS keychain for master key
- CLI commands: `set-secret`, `list-secrets`, `delete-secret`, `rotate-master-key`
- Secret resolution: encrypted vault first, environment variable fallback (for Docker)
- `.trading-system/keys.enc` vault file, never committed

Non-goals:

- cloud secret management
- team credential sharing
- browser-based secret entry
- production auth or authorization

### Milestone 11: Broker Boundary and Paper Trading

Status: complete. See `DOCS/milestone-11-issue-map.md` and `DOCS/ADR/011-broker-execution-boundary.md`.

Milestone 11 introduced the first broker execution boundary for paper trading practice without live broker calls.

Completed direction:

- accepted ADR for the broker execution boundary
- provider-agnostic broker port
- simulated paper broker adapter
- local `BrokerOrder` records and JSON persistence
- broker-imported fills linked to `OrderIntent`, `BrokerOrder`, and `Position`
- CLI commands for submit, sync, and show broker order

Non-goals:

- live Alpaca submission
- real-money execution
- FastAPI or React broker controls
- autonomous or automated trading
- recommendations or order-management-system behavior

### Milestone 12: Paper Execution Hardening

Status: complete. See `DOCS/milestone-12-issue-map.md` and `DOCS/post-milestone-11-roadmap.md`.

Harden the simulated paper workflow before adding a real broker adapter.

Candidate direction:

- broker-order list and inspection workflows
- clearer broker-order links in plan, position, and timeline views
- audit visibility for submitted, filled, canceled, rejected, and repeated sync cases
- simulated cancellation or rejection only if needed to test lifecycle behavior

Non-goals:

- Alpaca integration
- FastAPI or React broker controls
- real-money execution

### Milestone 13: Alpaca Paper Adapter

Status: complete. See `DOCS/milestone-13-issue-map.md`.

Add Alpaca paper-trading integration behind the accepted broker port after the simulated workflow is hardened.

Completed direction:

- Alpaca paper adapter behind `BrokerClient`
- vault-first, environment-fallback credential resolution for `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- submit from existing local `OrderIntent` and open local `Position` records only
- map Alpaca order and fill facts into local `BrokerOrder` and `Fill` records
- keep controls CLI-only for the first Alpaca slice

Non-goals:

- real-money execution
- browser execution controls
- broker positions becoming canonical local positions

### Milestones 14 Through 16: Reconciliation, Visibility, And Browser Controls

Status: future planned direction.

After Alpaca paper integration exists, the recommended sequence is:

- Milestone 14: broker reconciliation and status sync
- Milestone 15: read-only API/web broker visibility
- Milestone 16: human-controlled browser paper execution controls

Real-money execution remains a readiness gate, not a normal near-term milestone.

## Long-Term Product Direction

The longer-term product direction is a training, simulation, review, and decision-support system that helps the trader improve before increasing capital risk.

This is not an accepted implementation sequence yet. Each major phase needs explicit planning and, where architecture boundaries change, an ADR.

```text
V1 - Trading workflow foundation
V2 - Simulator / scenario replay
V3 - Insight engine and reporting
V4 - AI-assisted pattern explanation
V5 - RL / policy simulation
V6 - Paper trading integration
V7 - Real-money readiness gate
```

### V1: Trading Workflow Foundation

The system records intent, plans, rule evaluations, fills, position lifecycle, and reviews.

The main output is clean trade records and audit history.

### V2: Simulator / Scenario Replay

The system may later support scenario replay and playbook practice.

The main output would be labeled decisions, setup classifications, and mistake patterns.

### V3: Insight Engine And Reporting

The system may later provide deterministic or statistical insights over completed trades and simulator decisions.

The main output would be narrow pattern reports and mistake summaries, not automated recommendations.

### V4: AI-Assisted Pattern Explanation

AI may become useful after deterministic reporting exists and enough clean review data has accumulated.

Allowed direction:

- assistive pattern explanation
- natural-language summaries of existing data
- reminders based on past reviewed behavior

Non-goals:

- AI trade decisions
- AI-generated execution instructions
- policy learning

### V5: RL / Policy Simulation

Reinforcement learning belongs only after the system has mature structured data.

Allowed direction:

- policy simulation
- counterfactual analysis
- robustness testing across historical scenarios

Non-goals:

- autonomous trading
- replacing trader judgment
- learning from sparse or inconsistent records

### V6: Paper Trading Integration

Paper trading integration may become useful after the training and insight loops are stable.

Any integration must preserve the source-of-truth boundary between external execution facts and internal trade meaning.

### V7: Real-Money Readiness Gate

Real-money usage is a readiness gate, not a milestone by itself.

The system should first demonstrate that it can support consistent setup recognition, playbook selection, invalidation discipline, useful review, and stable paper-trading behavior.

## Learning-System Readiness Gates

AI or RL work must wait until the system has:

- stable manual workflows
- consistent review data
- reliable labels for setups, decisions, mistakes, and outcomes
- enough completed trades or scenarios to support meaningful analysis
- explicit success and failure definitions
- a separate accepted ADR for the learning-system boundary

The practical rule is:

```text
No intelligence before truth.
```

The current repository should first generate trustworthy ground truth. Learning systems are deferred until the data and workflow can support them.

## Related Documents

- [Milestones 3 To 5 Roadmap](milestones-3-to-5-roadmap.md)
- [Milestone 4 Market Context Design](milestone-4-market-context-design.md)
- [Milestone 5 Review Learning And Local Operations Design](milestone-5-review-learning-and-local-ops-design.md)
- [Milestone 6 Market Data Provider Design](milestone-6-market-data-provider-design.md)
- [Milestone 6 Market Data Provider Closeout](milestone-6-closeout.md)
- [ADR-005: MVP Definition and Boundaries](ADR/005-mvp-definition-and-boundaries.md)
- [ADR-006: Deferred Learning Systems Boundary](ADR/006-deferred-learning-systems-boundary.md)
- [ADR-007: Market Data Provider Boundary](ADR/007-market-data-provider-boundary.md)
- [Milestone 7 Closeout](milestone-7-closeout.md)
- [Milestone 9 Issue Map](milestone-9-issue-map.md)
- [ADR-010: Local Secret Vault Boundary](ADR/010-local-secret-vault-boundary.md)
- [Milestone 10 Issue Map](milestone-10-issue-map.md)
- [ADR-011: Broker Execution Boundary](ADR/011-broker-execution-boundary.md)
- [Milestone 11 Issue Map](milestone-11-issue-map.md)
- [Milestone 12 Issue Map](milestone-12-issue-map.md)
- [Milestone 13 Issue Map](milestone-13-issue-map.md)
- [Post-Milestone 11 Roadmap](post-milestone-11-roadmap.md)
