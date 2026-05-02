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

The accepted near-term sequence has advanced through Milestone 6.

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

Current sequencing:

- Milestone 6A: prototype-grade `yfinance` daily OHLCV snapshot fetch is complete.
- Milestone 6B Issue 1: provider-boundary hardening is complete.
- Milestone 6C Issue 1: Massive.com provider boundary is accepted in ADR-009.
- Milestone 6C Issue 2: narrow Massive.com daily bars adapter is complete.
- Milestone 6D: Milestone 6 closeout is complete.
- Next accepted direction: begin ADR-008 API-first web product work.

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

Status: next planned slice.

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

Status: outcome-level. Scope to be defined after Milestone 8.

Extend the browser interface beyond the initial trade-capture workflow to support daily use without the CLI.

Candidate direction:

- list and detail views for saved ideas, theses, and plans
- plan approval from the browser
- context attachment from the browser (link a market snapshot to a plan)
- a dashboard or activity summary for active captures

Non-goals:

- broker integration or execution
- automated trading or signals
- multi-user access or authentication

### Milestone 10: Secure Credentials

Status: outcome-level. Scope to be defined after Milestone 9.

Replace plain-text `.env` API key management with an encrypted local key vault for CLI use.

Candidate direction:

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

Status: outcome-level. Scope to be defined after Milestone 10. Requires V7 readiness criteria.

Introduce the first external execution boundary for paper trading practice.

Candidate direction:

- ADR for execution boundary (provider-agnostic, Alpaca as first implementation)
- Alpaca paper trading adapter behind the broker boundary
- Paper order intent → fill recording through the adapter
- Position and fill records remain in the local JSON store

Non-goals:

- real-money execution (gated by V7 readiness: consistent review data, stable playbook, clean trade records)
- autonomous or automated trading
- order management systems

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
