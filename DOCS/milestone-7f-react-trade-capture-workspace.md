# Milestone 7F React Trade Capture Workspace

Status: complete

Milestone 7F replaces the frontend runtime shell with the first focused browser workspace for API-first trade capture.

## Delivered Scope

- React/Vite trade-capture workspace as the first screen
- API health and reference count status strip
- raw trader-language input
- parse action using `POST /trade-capture/parse`
- editable `TradeIdea`, `TradeThesis`, and `TradePlan` draft sections
- field-level missing and ambiguous issue display using stable draft paths
- explicit save action using `POST /trade-capture/save`
- saved-result summary with generated idea, thesis, and plan ids
- responsive desktop and mobile layout

The workspace sends the current editable draft to save, not only the original raw source text.

## Not Included

7F does not implement:

- plan approval
- rule evaluation
- order intent creation
- position opening
- fill recording
- broker integration
- generated recommendations
- thesis claim verification
- API key vault behavior
- production auth, cloud deployment, or Postgres migration

## Validation

Validation recorded on 2026-05-02:

- `npm.cmd run build`: passed
- `uv run pytest tests\test_api_trade_capture.py tests\test_api_health.py`: 13 passed
- `uv run pytest`: 216 passed

## Next

The next Milestone 7 issue is 7G: End-to-End Save Workflow.
