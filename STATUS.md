# Trading System - Implementation Status

## Current Milestone

Milestones 1 through 14 are complete. Milestone 14 added CLI-only broker reconciliation and status sync after the Alpaca paper adapter.

## Implementation State

- Milestone 1: complete (MVP)
- Milestone 2: complete (core workflow extensions)
- Milestone 3: complete (manual workflow usability)
- Milestone 4: complete (read-only market context)
- Milestone 5: complete (review, learning, and local operations)
- Milestone 6: complete (read-only market data provider integration)
- Milestone 7: complete (API-first trade capture workspace)
- Milestone 8: complete (options chain ingestion)
- Milestone 9: complete (web product beyond first capture)
- Milestone 10: complete (secure credentials)
- Milestone 11: complete (broker boundary and simulated paper execution)
- Milestone 12: complete (paper execution hardening)
- Milestone 13: complete (Alpaca paper adapter)
- Milestone 14: complete (broker reconciliation and status sync)

The system is currently a functional local trading workflow with CLI and web entry points, local JSON persistence, lifecycle tracking, review/export support, local JSON operations, read-only context snapshots, API-first trade capture, options chain ingestion, browser-based plan inspection, approval, context attachment, CLI-only simulated paper broker execution, CLI-only Alpaca paper trading, and CLI-only broker reconciliation.

## Available Capabilities

- Structured trade workflow: `TradeIdea -> TradeThesis -> TradePlan`
- Trade plan approval and deterministic rule evaluation
- Position lifecycle management from approved plans
- Manual fill recording with optional `OrderIntent` linkage
- Automatic position state tracking and closure
- Read-side realized P&L for closed positions
- Trade review creation, tagging, quality scoring, filtering, inspection, and Markdown journal export
- Local JSON store validation, backup, and restore commands
- Lifecycle event audit trail and position timeline output
- CLI-based write and read workflows
- Filtering and sorting for core read models
- Explicit `OrderIntent` cancellation with audit visibility and fill-linkage enforcement
- Read-only market context snapshot import from local JSON files
- CLI inspection of stored market context by instrument or linked target
- Market context metadata surfaced alongside trade plan, position, and trade review detail views
- Broad `list-context` discovery filters for context type, source, observed range, and captured range
- `copy-context` workflow for copying an existing snapshot to a trade plan, position, or trade review target without mutating the original
- `fetch-market-data` fetches read-only daily OHLCV snapshots from yfinance or Massive.com
- `fetch-options-chain` fetches read-only options chain snapshots from yfinance or Massive.com
- FastAPI runtime skeleton with `GET /health`
- Vite React TypeScript frontend shell for the local web product
- Docker Compose runtime skeleton for backend and frontend containers
- Seeded reference lookup for instruments by symbol and playbooks by slug
- FastAPI reference endpoints for instruments and playbooks
- Trade-capture draft contracts with missing and ambiguous field reporting
- LiteLLM-backed trade-capture parser boundary with fake parser for tests
- FastAPI trade-capture parse, save, and saved-result retrieval endpoints
- React/Vite trade-capture workspace for parse, edit, save, and saved-result display
- FastAPI plan list, plan detail, and plan approval endpoints
- FastAPI market-context metadata listing and copy-to-plan attachment endpoint
- React/Vite workbench navigation for Capture, Plans, and Context
- Browser plan list filtering, plan detail inspection, draft approval, and context attachment
- Accepted local secret vault ADR for CLI credential storage
- Encrypted local secret vault with OS keychain-backed master key
- CLI secret commands: `set-secret`, `list-secrets`, `delete-secret`, `rotate-master-key`
- Vault-first, environment-fallback resolution for Massive.com provider API keys
- Provider-agnostic broker execution port with simulated paper adapter
- Local `BrokerOrder` persistence and audit events
- Broker-imported fills linked to `OrderIntent`, `BrokerOrder`, and `Position`
- CLI paper execution commands: `submit-paper-order`, `sync-paper-order`, `show-broker-order`
- Broker-order listing and linked-detail inspection for simulated paper execution
- Simulated paper-order cancellation and rejection workflows
- Alpaca paper broker adapter behind the existing `BrokerClient` port
- Vault-first, environment-fallback resolution for `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- CLI Alpaca paper submission through `submit-paper-order --provider alpaca`
- CLI Alpaca paper sync through `sync-paper-order` without simulated fill prices
- Alpaca broker order snapshot listing behind the broker port
- CLI batch sync for submitted broker orders through `sync-broker-orders --provider alpaca`
- CLI broker reconciliation through `reconcile-broker-orders --provider alpaca`
- Broker reconciliation mismatch audit events without redefining local trade meaning

## Active Constraints

- No real-money execution
- No automated execution
- No live market data streaming
- No AI or ML decision-making
- JSON persistence is the active local backend
- Postgres remains deferred as the active backend
- Domain model is the source of truth for trade meaning
- External data must remain read-only and non-canonical
- Broker data is external execution fact; local JSON remains source of truth for internal trade records

## Completed Slice (Milestone 4)

Milestone 4 is closed with the implemented local snapshot workflow:

- Context snapshots are imported from explicit local JSON files
- Snapshots can be attached to an instrument, trade plan, position, or trade review target
- Stored snapshots are timestamped and auditable
- Linked snapshots are visible in planning, position, and review inspection workflows
- Stored snapshots can be found by context type, source, date, instrument, and linked target
- Existing snapshots can be copied to a target without mutating the original import
- Context informs decisions but does not define trade meaning
- External provider implementation was deferred until the now-accepted ADR-007 boundary

## Completed Slice (Milestone 5)

Review tags and filtering are complete as the first narrow Milestone 5 implementation slice.

Review quality scores are complete as the second narrow Milestone 5 implementation slice.

Markdown journal export is complete as the third narrow Milestone 5 implementation slice.

Local JSON operations are complete as the fourth narrow Milestone 5 implementation slice.

Milestone 5 is complete because reviews can now be tagged, scored, filtered, inspected, exported to factual Markdown journals, and supported by explicit local JSON validation, backup, and restore commands without expanding into generated coaching, broad analytics, cloud operations, or automation.

## Completed Slice (Milestone 6A)

ADR-007 accepts the Milestone 6 market data provider boundary.

Milestone 6A is complete. The first provider slice implements `fetch-market-data` for optional prototype-grade `yfinance` daily OHLCV snapshots. Provider output is stored as explicit `MarketContextSnapshot` records before the rest of the application uses it. Provider data remains advisory and non-canonical.

Validation recorded on 2026-04-27:

- 6 focused yfinance market-data tests passed
- 162 full-suite tests passed

Closeout is recorded in `DOCS/milestone-6a-yfinance-market-data-closeout.md`.

## Completed Slice (Milestone 6B Issue 1)

Milestone 6B Issue 1 is complete. The `fetch-market-data` command now resolves provider-backed market data through an explicit provider registry instead of directly constructing yfinance from the CLI.

The CLI supports:

```powershell
uv run trading-system fetch-market-data AAPL --provider yfinance --start 2026-04-01 --end 2026-04-30
```

Existing calls without `--provider` still default to yfinance. Unsupported providers fail clearly. yfinance remains the default provider.

Focused validation recorded on 2026-04-27:

- 10 focused provider-boundary tests passed
- 166 full-suite tests passed

Closeout is recorded in `DOCS/milestone-6b-provider-boundary-hardening-closeout.md`.

## Completed Slice (Milestone 6C Issue 1)

Milestone 6C Issue 1 is complete. ADR-009 accepts Massive.com, formerly Polygon.io, as the next provider candidate after yfinance.

ADR-009 records:

- official `massive` Python client as the preferred first implementation path
- `MASSIVE_API_KEY` as the initial credential boundary
- daily aggregate/OHLCV-style bars as the first data shape
- `MarketContextSnapshot` as the storage boundary
- yfinance remains the default provider until a later decision changes it

No Massive.com dependency or runtime adapter was added by Issue 1.

## Completed Slice (Milestone 6C Issue 2)

Milestone 6C Issue 2 is complete. The system now has a narrow Massive.com daily bars adapter behind the existing provider registry.

The CLI supports:

```powershell
uv run trading-system fetch-market-data AAPL --provider massive --start 2026-04-01 --end 2026-04-30
```

Massive-backed fetches require `MASSIVE_API_KEY`. They use the official `massive` Python client, store snapshots with `source = "massive"`, and keep provider data read-only, advisory, and non-canonical. yfinance remains the default provider.

Focused validation recorded on 2026-04-29:

- 21 focused market-data tests passed
- 177 full-suite tests passed

Closeout is recorded in `DOCS/milestone-6c-massive-daily-bars-closeout.md`.

## Completed Slice (Milestone 6D)

Milestone 6D is complete. Milestone 6 is closed with two implemented provider paths behind the market-data provider boundary.

Final Milestone 6 state:

- yfinance remains the default provider.
- Massive.com is available through `--provider massive`.
- Massive-backed fetches require `MASSIVE_API_KEY`.
- Daily OHLCV snapshots remain read-only, advisory, and non-canonical.
- Provider response objects stay inside infrastructure adapters.
- No automatic fallback exists between providers.

Final validation recorded on 2026-04-29:

- 177 full-suite tests passed

Closeout is recorded in `DOCS/milestone-6-closeout.md`.

## Completed Slice (Milestone 7A)

Milestone 7A is the Dockerized runtime foundation for the API-first trade-capture workspace.

This slice adds a minimal FastAPI entrypoint, a Vite React TypeScript frontend shell, Docker Compose for the backend and frontend, and host Ollama environment placeholders for later LiteLLM parser work.

Milestone 7A intentionally does not add reference lookup, draft contracts, natural-language parsing, save workflow, approval, execution, positions, fills, broker integration, or recommendations.

Validation recorded on 2026-04-29:

- 1 focused API health test passed
- 178 full-suite tests passed
- frontend install completed with 0 vulnerabilities
- frontend production build passed
- Docker Compose config was valid
- Docker Compose built and started `api` and `web`
- API health returned `{"status":"ok"}`
- web endpoint returned HTTP 200

## Completed Slice (Milestone 7B)

Milestone 7B is the reference lookup foundation for API-first trade capture.

This slice adds a `Playbook` reference entity, read-only reference-data repository port, seeded local instruments and playbooks, a reference lookup service, FastAPI reference endpoints, and frontend shell display of reference counts.

User-facing lookup now works with symbols such as `NVDA` and playbook slugs such as `pullback-to-trend`. Internal UUIDs remain available in API responses for later save workflows, but they are not the user-facing lookup input.

Milestone 7B intentionally does not add reference management screens, draft schemas, natural-language parsing, save workflow, approval, execution, positions, fills, broker integration, or recommendations.

Validation recorded on 2026-04-29:

- 8 focused reference/API tests passed
- 185 full-suite tests passed
- frontend production build passed

## Completed Slice (Milestone 7C)

Milestone 7C is the trade-capture draft contract for the future parser, API, and frontend workflow.

This slice adds editable draft contracts for `TradeIdea`, `TradeThesis`, and `TradePlan`, required and optional field definitions, stable API/UI field paths, missing-field reporting, ambiguous-field reporting, and save-readiness checks for parsed-but-unsaved trade capture state.

Milestone 7C intentionally does not add natural-language parsing, LiteLLM/Ollama calls, trade-capture endpoints, local JSON save workflow, frontend capture workspace, approval, execution, positions, fills, broker integration, recommendations, or claim verification.

Validation recorded on 2026-05-02:

- 6 focused trade-capture draft tests passed
- 14 focused trade-capture/reference/API tests passed
- 191 full-suite tests passed

## Completed Slice (Milestone 7D)

Milestone 7D is the natural-language parser boundary for future API-first trade capture.

This slice adds a `TradeCaptureParser` port, `TradeCaptureParseError`, deterministic fake parser, LiteLLM-backed parser adapter, environment-based model/API-base configuration, strict extraction prompt, JSON response validation, and mapping into the Milestone 7C draft contract.

Milestone 7D intentionally does not add trade-capture endpoints, frontend capture workspace, local JSON save workflow, persistence from parser output, approval, execution, positions, fills, broker integration, recommendations, or claim verification.

Validation recorded on 2026-05-02:

- 22 focused trade-capture draft/parser tests passed
- 30 focused trade-capture/reference/API tests passed
- 207 full-suite tests passed

## Completed Slice (Milestone 7E)

Milestone 7E is the FastAPI trade-capture service for the future web workspace.

This slice adds backend schemas, a `TradeCaptureService`, `POST /trade-capture/parse`, `POST /trade-capture/save`, and `GET /trade-capture/saved/{trade_plan_id}`. The API parses into editable drafts without persistence, saves confirmed drafts into linked `TradeIdea`, `TradeThesis`, and `TradePlan` records, and retrieves compact saved-result summaries.

Milestone 7E intentionally does not add the React capture workspace, browser-backed end-to-end workflow, approval, rule evaluation, order intents, positions, fills, broker integration, recommendations, claim verification, production auth, cloud deployment, or Postgres migration.

Validation recorded on 2026-05-02:

- 31 focused trade-capture API/parser/draft tests passed
- 39 focused trade-capture/reference/API tests passed
- 216 full-suite tests passed

## Completed Slice (Milestone 7F)

Milestone 7F is the React/Vite trade-capture workspace.

This slice replaces the frontend runtime shell with the first browser workflow for raw trade-language input, parse action, editable Idea/Thesis/Plan draft sections, missing and ambiguous field indicators, explicit save, and saved-result summary.

Milestone 7F intentionally does not add approval, rule evaluation, order intent creation, position opening, fill recording, broker integration, generated recommendations, claim verification, API key vault behavior, production auth, cloud deployment, or Postgres migration.

Validation recorded on 2026-05-02:

- frontend production build passed
- 13 focused trade-capture/API tests passed
- 216 full-suite tests passed

## Completed Slice (Milestone 7G)

Milestone 7G is the end-to-end save workflow acceptance slice.

This slice validates the full parse→edit→save→persist workflow through Docker and the live API. No new domain features were added. Changes made during acceptance:

- Switched LLM provider from Ollama to Groq (`groq/qwen/qwen3-32b`) via `.env` and `TRADING_SYSTEM_LLM_API_BASE`
- Added `env_file` support to `docker-compose.yml` so secrets in `.env` reach the api container
- Hardened `_string_list` in the LiteLLM parser to coerce a bare string to a single-element list
- Hardened `_ambiguous_issue` candidates to coerce non-string types rather than raise

Validation recorded on 2026-05-02:

- `docker compose up --build`: api and web containers healthy
- `POST /trade-capture/parse`: correctly extracts fields and surfaces validation issues
- `POST /trade-capture/save`: creates linked `TradeIdea`, `TradeThesis`, `TradePlan` records
- `GET /trade-capture/saved/{trade_plan_id}`: retrieves saved result summary
- Local JSON store confirmed to contain all three linked records with `approval_state: draft`
- All error states verified: empty input, missing required fields, ambiguous fields, unknown symbol, unknown plan ID
- `uv run pytest`: 216 passed

## Completed Slice (Milestone 7H)

Milestone 7H is the Milestone 7 closeout.

This slice produces the milestone closeout document, adds the web interface section to the README, records final validation results, and updates the knowledge base. No new domain features were added.

Validation recorded on 2026-05-02:

- `uv run pytest`: 216 passed
- `npm.cmd run build`: passed
- `docker compose up --build`: api and web containers healthy
- `curl http://localhost:8000/health`: `{"status": "ok"}`

## Completed Slice (Milestone 8)

Milestone 8 is Options Chain Ingestion.

This slice adds `YFinanceOptionsChainImportSource` and `MassiveOptionsChainImportSource` behind a new `create_options_chain_source()` registry method, and a `fetch-options-chain` CLI command. Options chains are stored as `context_type: options_chain` MarketContextSnapshots and are linkable to plans, positions, or reviews.

Also in this slice: `load_dotenv()` added to the CLI so `.env` API keys work for `uv run` commands without Docker; `fetch-market-data` and `create-trade-idea` now accept ticker symbols instead of requiring raw UUIDs; Massive.com daily bar volume parsing hardened to use `round()`.

Note: Massive.com options data requires a paid plan. The adapter is implemented; live execution returns a clear upgrade message on the free tier.

Validation recorded on 2026-05-02:

- `uv run trading-system fetch-options-chain AAPL --expiry 2026-05-22 --provider yfinance`: snapshot stored with full calls and puts
- `uv run trading-system fetch-market-data AAPL --provider massive --start 2026-04-01 --end 2026-04-30`: daily OHLCV stored
- `uv run pytest`: 233 passed

## Completed Slice (Milestone 9)

Milestone 9 is Web Product Beyond First Capture.

This slice extends the local browser product beyond first save. The React/Vite interface now has Capture, Plans, and Context views. Plans is the primary workbench view: saved plans can be filtered by approval state, sorted by created time, inspected with linked idea/thesis/plan detail, approved when still draft, and linked to existing market context snapshots by copying instrument-matching snapshots to the plan.

The FastAPI surface now includes:

- `GET /trade-plans`
- `GET /trade-plans/{trade_plan_id}`
- `POST /trade-plans/{trade_plan_id}/approve`
- `GET /market-context`
- `POST /market-context/{snapshot_id}/copy-to-target`

Milestone 9 intentionally does not add broker integration, execution, order intent creation, position opening, fill recording, generated recommendations, authentication, key vault behavior, Postgres migration, or rule evaluation before approval.

Validation recorded on 2026-05-03:

- `uv run pytest tests\test_api_trade_capture.py tests\test_api_trade_plans.py`: 15 passed
- `uv run pytest`: 239 passed
- `npm.cmd run build`: passed
- `docker compose up --build -d`: api and web containers started
- `GET /health`: `{"status":"ok"}`

## Completed Slice (Milestone 10)

Milestone 10 is Secure Credentials.

This slice adds ADR-010, a local encrypted secret vault boundary, CLI secret management commands, and vault-first credential resolution for Massive.com provider API keys. Environment fallback remains supported for Docker, CI, and existing `.env` workflows.

The CLI now supports:

- `set-secret`
- `list-secrets`
- `delete-secret`
- `rotate-master-key`

Milestone 10 intentionally does not add cloud secret management, team/shared vaults, browser secret entry, production authentication or authorization, key synchronization, remote backup, or live broker credentials for real-money execution.

Validation recorded on 2026-05-03:

- `uv run pytest tests\test_local_secret_vault.py tests\test_cli_secrets.py tests\test_massive_market_data_source.py tests\test_massive_options_chain_source.py tests\test_cli_market_data_fetch.py`: 30 passed
- `uv run pytest`: 246 passed

## Completed Slice (Milestone 13)

Milestone 13 is Alpaca Paper Adapter.

This slice adds the first live paper broker adapter behind the existing provider-agnostic broker port. Alpaca paper submission uses the official `alpaca-py` SDK, resolves `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` through the local vault before environment fallback, and maps local `OrderIntent` records into Alpaca market, limit, stop, and stop-limit requests. Sync maps Alpaca statuses into local `BrokerOrderStatus` and imports local `Fill` records only after Alpaca reports a filled order with an average fill price.

Milestone 13 intentionally does not add real-money execution, FastAPI broker endpoints, React broker controls, browser execution buttons, broker-position reconciliation, autonomous trading, or full order-management-system behavior.

Validation recorded on 2026-05-03:

- `uv run pytest tests\test_alpaca_paper_broker.py tests\test_broker_execution_service.py tests\test_cli_workflow_commands.py`: 44 passed
- `uv run pytest`: 280 passed

## Next Slice

Milestone 14: Broker Reconciliation And Status Sync. See `DOCS/post-milestone-11-roadmap.md`.

## Immediate Design Guardrails

- Do not couple context data to domain entities as canonical trade meaning
- Do not introduce execution triggers or automation
- Do not stream or subscribe to live data
- Keep all context interactions explicit and user-invoked
- Preserve auditability of retrieved context
- Keep provider response objects and schemas out of domain logic
- Keep any future provider data-shape expansion behind a new explicit issue or ADR update
- Treat `yfinance` as prototype-grade, not production-grade market data infrastructure

## Architecture Reference (Current)

Authoritative documents for implementation:

- `DOCS/systems-blueprint.md`
- `DOCS/domain-model.md`
- `DOCS/ADR/`
- `DOCS/milestone-6-market-data-provider-design.md`
- `DOCS/ADR/009-massive-provider-boundary.md`
- `DOCS/ADR/008-api-first-web-product-and-trade-capture-drafts.md`
- `DOCS/milestone-7-issue-map.md`
- `DOCS/milestone-7a-runtime-skeleton.md`
- `DOCS/milestone-7b-reference-lookup-foundation.md`
- `DOCS/milestone-7c-trade-capture-draft-contract.md`
- `DOCS/milestone-7d-natural-language-parser-boundary.md`
- `DOCS/milestone-7e-fastapi-trade-capture-service.md`
- `DOCS/milestone-7f-react-trade-capture-workspace.md`
- `DOCS/milestone-9-issue-map.md`
- `DOCS/ADR/010-local-secret-vault-boundary.md`
- `DOCS/milestone-10-issue-map.md`
- `DOCS/ADR/011-broker-execution-boundary.md`
- `DOCS/milestone-11-issue-map.md`
- `DOCS/milestone-12-issue-map.md`
- `DOCS/milestone-13-issue-map.md`

The domain model remains the canonical source of truth for entities and relationships.

## External Design Context

For design rationale, open questions, and knowledge synthesis:

```text
C:\Users\bosto\dockerstuff\knowledge-base\trading-system\
```

## Update Rule

Update this file when:

- milestone status changes
- a new implementation slice begins or completes
- capabilities materially change
- architectural references are updated

Keep this file concise and factual. Do not include exploratory design notes.
