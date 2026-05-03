# Milestone 9 Issue Map: Web Product Beyond First Capture

Milestone 9 makes the browser useful after the first trade capture is saved. The web product now centers on saved trade plans: list, inspect, approve, and attach existing read-only market context snapshots to a plan.

## Issues

### 9A: FastAPI Plan Read And Approval Endpoints

Add plan-centered API routes for browser workflows.

- `GET /trade-plans?approval_state=&sort=` returns plan summaries with linked idea metadata, display symbol and playbook when resolvable, approval state, created time, and linked context count.
- `GET /trade-plans/{trade_plan_id}` returns linked idea, thesis, plan, rule evaluations, order intents, positions, and market context metadata.
- `POST /trade-plans/{trade_plan_id}/approve` reuses `TradePlanningService.approve_trade_plan()` and returns refreshed detail.

Status: complete.

### 9B: FastAPI Market Context Discovery And Attachment

Add metadata-only context discovery and explicit plan attachment.

- `GET /market-context?instrument_id=&target_type=&target_id=&context_type=&source=` returns snapshot metadata only.
- `POST /market-context/{snapshot_id}/copy-to-target` accepts `target_type: "TradePlan"` and `target_id`, then copies the existing snapshot through `MarketContextImportService`.
- Context payloads are not rendered or returned through the browser discovery/detail contracts.

Status: complete.

### 9C: React Local Workbench

Extend the single capture screen into a compact workbench.

- Top navigation: Capture, Plans, Context.
- Plans view supports approval-state filtering and newest/oldest sort.
- Plan detail shows Idea, Thesis, Plan, linked record counts, linked market context metadata, and draft approval.
- Context attachment panel lists instrument-matching existing snapshots and attaches by copying to the selected plan.

Status: complete.

### 9D: Milestone 9 Closeout

Docs, status, roadmap, and validation.

Status: complete.

## Boundary

Milestone 9 does not add broker integration, execution, order intent creation, position opening, fill recording, generated recommendations, authentication, key vault behavior, Postgres migration, or rule evaluation before approval.

Approval from the browser mirrors existing CLI/service approval behavior only. Market context attachment copies existing snapshots to a plan; it does not fetch new provider data from the browser.

## Validation

Recorded on 2026-05-03:

- `uv run pytest tests\test_api_trade_capture.py tests\test_api_trade_plans.py`: 15 passed
- `uv run pytest`: 239 passed
- `npm.cmd run build`: passed
- `docker compose up --build -d`: api and web containers started
- `GET /health`: `{"status":"ok"}`
