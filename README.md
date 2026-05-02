---

# trading-system

A professional-grade personal trading system for structured discretionary trading.

---

## Purpose

This project is designed to help a single trader:

- manage trades with full context
- enforce discipline and process
- separate intent from execution
- capture execution reality
- review and improve decision-making over time

This is **not**:

- a trading bot
- a black-box system
- an automated execution engine

It is a **structured, auditable trading workflow system**.

---

## Core Principles

- **Structured trade representation**
  Every trade has intent, thesis, and a plan before execution.

- **Deterministic discipline**
  Hard rules are explicit, enforceable, and auditable.

- **Separation of concerns**
  - intent (`TradePlan`)
  - execution intent (`OrderIntent`)
  - execution fact (`Fill`)
  - outcome (`Position`)
  - reflection (`TradeReview`)

- **Canonical domain model**
  The system owns trade meaning. External systems only provide facts.

- **Incremental evolution**
  Start simple. Expand only when justified.

---

## Architecture

The system follows a **modular monolith** architecture:

```text
src/trading_system/
```

Modules:

- `app/` - CLI entrypoints
- `domain/` - business logic and entities
- `services/` - use-case orchestration
- `rules_engine/` - deterministic rule evaluation
- `ports/` - interfaces and persistence boundaries
- `infrastructure/` - persistence and adapters

See:

- `DOCS/ADR/001-system-architecture.md`
- `DOCS/ADR/002-rules-vs-context.md`
- `DOCS/ADR/003-development-and-deployment-strategy.md`
- `DOCS/ADR/004-canonical-domain-and-source-of-truth.md`
- `DOCS/ADR/005-mvp-definition-and-boundaries.md`
- `DOCS/ADR/006-deferred-learning-systems-boundary.md`
- `DOCS/ADR/007-market-data-provider-boundary.md`
- `DOCS/ADR/008-api-first-web-product-and-trade-capture-drafts.md`
- `DOCS/domain-model.md`
- `DOCS/milestone-1-summary.md`
- `DOCS/milestone-2-roadmap.md`
- `DOCS/milestones-3-to-5-roadmap.md`
- `DOCS/milestone-4-market-context-design.md`
- `DOCS/milestone-4-summary.md`
- `DOCS/milestone-5-review-learning-and-local-ops-design.md`
- `DOCS/milestone-6-market-data-provider-design.md`
- `DOCS/milestone-7-issue-map.md`
- `DOCS/milestone-7a-runtime-skeleton.md`
- `DOCS/milestone-7b-reference-lookup-foundation.md`
- `DOCS/milestone-7c-trade-capture-draft-contract.md`

---

## Core Workflow

```text
TradeIdea -> TradeThesis -> TradePlan -> plan approval -> RuleEvaluation -> OrderIntent -> Position -> Fill -> Position close -> TradeReview
```

`LifecycleEvent` records auditable state transitions throughout the lifecycle.

---

## How To Use This System

The current repository provides a CLI-driven, manual trading workflow built on the completed Milestone 1 MVP and extended by Milestone 2 implementation work.

### Typical Flow

1. Define the trade:
   - create `TradeIdea`
   - create `TradeThesis`
   - create `TradePlan`
2. Validate discipline:
   - approve the plan
   - run rule evaluation
3. Execute manually:
   - create an `OrderIntent` from the approved plan
   - open a `Position`
   - record `Fill` entries as trades execute
4. Let the system track state:
   - position updates automatically from fills
   - position closes automatically when quantity reaches zero
   - realized P&L is derived on the read side for closed positions
5. Review the trade:
   - create a `TradeReview` after closure

### Run The Demo

```powershell
uv run trading-system demo-planned-trade
```

The demo uses local JSON persistence. By default it writes to:

```text
.trading-system/store.json
```

Set `TRADING_SYSTEM_STORE_PATH` to use a different local file.

### Core Write Workflow

```powershell
uv run trading-system create-trade-idea --instrument-id <instrument-id> --playbook-id <playbook-id> --purpose swing --direction long --horizon days_to_weeks
uv run trading-system create-trade-thesis <trade-idea-id> --reasoning "Setup has a catalyst."
uv run trading-system create-trade-plan --trade-idea-id <trade-idea-id> --trade-thesis-id <trade-thesis-id> --entry-criteria "Breakout confirmation." --invalidation "Close below setup low." --risk-model "Defined stop and max loss."
uv run trading-system approve-trade-plan <trade-plan-id>
uv run trading-system evaluate-trade-plan-rules <trade-plan-id>
uv run trading-system create-order-intent --trade-plan-id <trade-plan-id> --symbol AAPL --side buy --order-type limit --quantity 100 --limit-price 25.50
uv run trading-system cancel-order-intent <order-intent-id>
uv run trading-system open-position <trade-plan-id>
uv run trading-system record-fill --position-id <position-id> --side buy --quantity 100 --price 25.50 --order-intent-id <order-intent-id>
uv run trading-system record-fill --position-id <position-id> --side sell --quantity 100 --price 27.00
uv run trading-system create-trade-review --position-id <position-id> --summary "Followed the plan." --what-went-well "Entry was clean." --what-went-poorly "Exit could have been faster." --tag risk-management --tag missed-exit --process-score 5 --setup-quality 4 --execution-quality 3 --exit-quality 2
```

### Read And Inspect Stored Data

```powershell
uv run trading-system list-trade-ideas
uv run trading-system list-trade-ideas --purpose swing --direction long --status draft --sort newest
uv run trading-system list-trade-theses
uv run trading-system list-trade-theses --has-plan --sort newest
uv run trading-system show-trade-thesis <trade-thesis-id>
uv run trading-system list-trade-plans
uv run trading-system list-trade-plans --approval-state approved --sort newest
uv run trading-system show-trade-plan <trade-plan-id>
uv run trading-system list-trade-reviews
uv run trading-system list-trade-reviews --rating 4 --purpose swing --direction long --tag risk-management --process-score 5 --sort newest
uv run trading-system show-trade-review <trade-review-id>
uv run trading-system export-review-journal --output .\journal.md
uv run trading-system export-review-journal --output .\missed-exits.md --tag missed-exit --sort newest
uv run trading-system validate-store
uv run trading-system backup-store --output-dir .\.trading-system\backups
uv run trading-system restore-store .\.trading-system\backups\<backup-file>.json --overwrite
uv run trading-system list-positions
uv run trading-system list-positions --state closed --sort newest
uv run trading-system list-positions --purpose swing --has-review
uv run trading-system show-position <position-id>
uv run trading-system show-position-timeline <position-id>
```

### Read-Only Market Context

Milestone 4 delivered explicit local JSON file import for market/context snapshots. Context is advisory support for planning and review; it does not change trade plans, positions, reviews, rules, fills, or lifecycle state.

Example context file:

```json
{
  "context_type": "price_snapshot",
  "observed_at": "2026-04-26T16:00:00-04:00",
  "payload": {
    "symbol": "AAPL",
    "last": "185.25",
    "notes": "Delayed close snapshot"
  }
}
```

Import and inspect context:

```powershell
uv run trading-system import-context .\context.json --instrument-id <instrument-id>
uv run trading-system import-context .\context.json --target-type trade-plan --target-id <trade-plan-id>
uv run trading-system import-context .\context.json --target-type position --target-id <position-id>
uv run trading-system import-context .\context.json --target-type trade-review --target-id <trade-review-id>
uv run trading-system copy-context <market-context-snapshot-id> --target-type trade-plan --target-id <trade-plan-id>
uv run trading-system list-context
uv run trading-system list-context --instrument-id <instrument-id>
uv run trading-system list-context --target-type trade-plan --target-id <trade-plan-id>
uv run trading-system list-context --context-type price_snapshot --source local-file --observed-from 2026-04-26T00:00:00+00:00 --observed-to 2026-04-26T23:59:59+00:00
uv run trading-system fetch-market-data AAPL --start 2026-04-01 --end 2026-04-30
uv run trading-system fetch-market-data AAPL --provider yfinance --start 2026-04-01 --end 2026-04-30
uv run trading-system fetch-market-data AAPL --provider massive --start 2026-04-01 --end 2026-04-30
uv run trading-system fetch-market-data AAPL --start 2026-04-01 --end 2026-04-30 --target-type trade-plan --target-id <trade-plan-id>
uv run trading-system show-context <market-context-snapshot-id>
```

Linked snapshots also appear as metadata-only `Market context` sections in `show-trade-plan`, `show-position`, and `show-trade-review`. Use `show-context` when you need to inspect the full stored payload. `copy-context` creates a new linked snapshot from an existing one; it does not mutate the original import.

ADR-007 and ADR-009 define the Milestone 6 provider boundary. Milestone 6 is complete: `fetch-market-data` stores provider-backed daily OHLCV snapshots as explicit `MarketContextSnapshot` records. `yfinance` remains the default provider; `--provider yfinance` and `--provider massive` are both accepted explicitly. Massive.com fetches require `MASSIVE_API_KEY`. External data remains read-only, advisory, and non-canonical.

## Review Tags

Milestone 5 starts with creation-time review tags for local learning loops. Tags are simple lowercase slugs stored on `TradeReview`, shown in review list/detail output, and filterable through repeated `--tag` options.

```powershell
uv run trading-system create-trade-review --position-id <position-id> --summary "Followed the plan." --what-went-well "Entry was clean." --what-went-poorly "Exit was late." --tag missed-exit --tag risk-management
uv run trading-system list-trade-reviews --tag missed-exit
uv run trading-system list-trade-reviews --tag missed-exit --tag risk-management
```

Tags do not introduce review editing, a central taxonomy, coaching, or analytics.

## Review Quality Scores

The second Milestone 5 slice adds optional 1-5 quality scores to make reviews easier to compare later without introducing reports or generated coaching.

```powershell
uv run trading-system create-trade-review --position-id <position-id> --summary "Followed the plan." --what-went-well "Entry was clean." --what-went-poorly "Exit was late." --process-score 5 --setup-quality 4 --execution-quality 3 --exit-quality 2
uv run trading-system list-trade-reviews --process-score 5
uv run trading-system list-trade-reviews --setup-quality 4 --execution-quality 3
```

Scores are creation-time review metadata only. Existing reviews do not need scores.

## Review Journal Export

The third Milestone 5 slice adds a narrow Markdown journal export for completed reviewed trades. It reuses the same filters as `list-trade-reviews` and writes factual review data to a user-provided local file.

```powershell
uv run trading-system export-review-journal --output .\journal.md
uv run trading-system export-review-journal --output .\missed-exits.md --tag missed-exit --sort newest
uv run trading-system export-review-journal --output .\journal.md --overwrite
```

The export includes review identity, reviewed time, linked position and trade plan ids, purpose, direction, realized P&L, tags, quality scores, review notes, lessons, follow-up actions, and linked market-context metadata. It does not include full context payloads; use `show-context` for payload inspection. Existing output files are not replaced unless `--overwrite` is provided.

## Local JSON Operations

The active local backend is a single JSON store. Use the operational commands to validate, back up, and restore that file explicitly.

```powershell
uv run trading-system validate-store
uv run trading-system backup-store
uv run trading-system backup-store --output-dir .\.trading-system\backups
uv run trading-system restore-store .\.trading-system\backups\<backup-file>.json --overwrite
```

Backups are exact timestamped JSON copies of the configured store and default to `.trading-system/backups`. Restore validates the backup before replacing the configured store and requires `--overwrite` when the store already exists.

### Important Notes

- execution is manual
- prices and fills are user-entered
- data persists locally in JSON by default
- no broker integration exists yet
- market context exists as explicit read-only local snapshots; `fetch-market-data` supports yfinance and Massive.com daily-OHLCV ingestion paths behind the same boundary
- the system is currently a discipline and journaling tool

---

## MVP Boundary

Milestone 1 is the MVP boundary defined by ADR-005.

The MVP is:

> A local, CLI-driven trading system that enforces structured trade intent, captures execution via manual fills, and supports post-trade review with full auditability.

### MVP Includes

- structured trade definition (`TradeIdea -> TradeThesis -> TradePlan`)
- deterministic rule evaluation
- position creation from approved plans
- manual fill recording
- automatic position state tracking
- automatic position closure
- one structured trade review per position
- lifecycle audit trail

### MVP Does Not Include

- broker integration
- automated execution
- market data feeds
- advanced P&L analytics
- dashboards or UI
- AI-generated insights

The MVP focuses on disciplined, auditable workflow rather than automation.

---

## Status

See `STATUS.md` for current implementation state and next steps.

| Layer | File | Role |
| --- | --- | --- |
| Why | External knowledge base | reasoning, intent, exploration |
| What (design) | `DOCS/` | architecture and domain |
| What (current reality) | `STATUS.md` | implementation snapshot |
| How to use | `README.md` | user and workflow guide |

---

## Local Development

This project uses `uv`.

Run tests:

```powershell
uv run pytest
```

Run CLI:

```powershell
uv run trading-system version
uv run trading-system --help
```

### Local Web Runtime

Milestone 7A adds the first local web/API runtime shell. This slice is complete.

Run the Dockerized app shell:

```powershell
docker compose up --build
```

Open the web app:

```text
http://localhost:5173
```

Check the API directly:

```text
http://localhost:8000/health
```

This web shell does not implement trade capture yet. Draft contracts now exist for later parser/API/UI work, but parser behavior, trade-capture endpoints, and save workflow are planned for later Milestone 7 issues.

Host Ollama is expected at:

```text
http://host.docker.internal:11434
```

### Reference Lookup API

Milestone 7B adds seeded local reference lookup for the future trade-capture workflow.

```text
GET http://localhost:8000/reference/instruments
GET http://localhost:8000/reference/instruments/NVDA
GET http://localhost:8000/reference/playbooks
GET http://localhost:8000/reference/playbooks/pullback-to-trend
```

These endpoints let web/API workflows use symbols and playbook slugs instead of user-entered UUIDs.

---

## Knowledge Base

This project uses a split knowledge model.

Repository sources of truth:

- `DOCS/ADR/` for versioned architectural decisions
- `DOCS/` for domain and milestone documents

External knowledge base:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

It captures canonical entity notes, cross-topic synthesis, processed implementation notes, and exploratory future-direction documents.

---

## Final Note

This system is built to enforce thinking quality, not just track trades.

If it feels manual, that is intentional. Automation should only be added on top of a correct and auditable foundation.
