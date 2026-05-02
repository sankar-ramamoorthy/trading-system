# Milestone 7C Trade Capture Draft Contract

Status: complete

Milestone 7C defines the editable draft contract for the API-first trade-capture workflow accepted in ADR-008.

## Delivered Scope

- Editable `TradeIdeaDraft`, `TradeThesisDraft`, and `TradePlanDraft` contracts
- Top-level `TradeCaptureDraft` for parsed-but-unsaved trade capture state
- Required save-field definitions for:
  - instrument symbol
  - playbook slug
  - purpose
  - direction
  - horizon
  - thesis reasoning
  - entry criteria
  - invalidation
- Optional field definitions for:
  - supporting evidence
  - risks
  - disconfirming signals
  - targets
  - risk model
  - sizing assumptions
- Stable field paths such as `TradeIdea.instrument_symbol` for API and UI issue reporting
- Missing and ambiguous field issue reporting
- Readiness checks that block save when required fields are missing or parser ambiguity remains

The contract uses user-facing instrument symbols and playbook slugs. Internal UUID resolution remains a later save/API concern.

## Not Included

7C does not implement:

- natural-language parsing
- LiteLLM or Ollama calls
- FastAPI trade-capture endpoints
- local JSON save workflow
- frontend trade-capture workspace
- approval, rule evaluation, order intent, position, fill, broker, recommendation, or claim-verification behavior

## Validation

Validation recorded on 2026-05-02:

- `uv run pytest tests\test_trade_capture_draft.py`: 6 passed
- `uv run pytest tests\test_trade_capture_draft.py tests\test_reference_lookup_service.py tests\test_api_health.py`: 14 passed
- `uv run pytest`: 191 passed

## Next

The next Milestone 7 issue is 7D: Natural-Language Parser Boundary.
