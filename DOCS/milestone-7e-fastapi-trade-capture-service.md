# Milestone 7E FastAPI Trade Capture Service

Status: complete

Milestone 7E exposes backend trade-capture workflows through FastAPI over the parser, reference lookup, planning service, query service, and local JSON repositories.

## Delivered Scope

- FastAPI trade-capture schemas for editable drafts, field issues, parse responses, save responses, and saved-result summaries
- `TradeCaptureService` for API orchestration
- `POST /trade-capture/parse`
- `POST /trade-capture/save`
- `GET /trade-capture/saved/{trade_plan_id}`
- API wiring to the configured local JSON store through `TRADING_SYSTEM_STORE_PATH`
- test injection support for fake parsers and temporary repositories

The save workflow resolves user-facing instrument symbols and playbook slugs through the seeded reference lookup foundation, then creates linked `TradeIdea`, `TradeThesis`, and `TradePlan` records through existing services.

## Endpoint Behavior

`POST /trade-capture/parse` parses raw source text into an editable draft and returns validation issues plus `ready_to_save`. It does not persist records.

`POST /trade-capture/save` accepts a confirmed editable draft, rejects missing or ambiguous required fields, rejects unknown symbols or playbook slugs, and saves linked idea/thesis/plan records.

`GET /trade-capture/saved/{trade_plan_id}` returns a compact saved result summary for a saved trade plan.

## Not Included

7E does not implement:

- React/Vite capture workspace
- full browser-backed parse/edit/save acceptance workflow
- plan approval
- rule evaluation
- order intent creation
- position opening
- fill recording
- broker integration
- generated recommendations
- thesis claim verification
- production auth, cloud deployment, or Postgres migration

## Validation

Validation recorded on 2026-05-02:

- `uv run pytest tests\test_api_trade_capture.py tests\test_trade_capture_parser.py tests\test_trade_capture_draft.py`: 31 passed
- `uv run pytest tests\test_api_trade_capture.py tests\test_trade_capture_parser.py tests\test_trade_capture_draft.py tests\test_reference_lookup_service.py tests\test_api_health.py`: 39 passed
- `uv run pytest`: 216 passed

## Next

The next Milestone 7 issue is 7F: React/Vite Trade Capture Workspace.
