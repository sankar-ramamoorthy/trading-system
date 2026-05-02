# Milestone 7D Natural-Language Parser Boundary

Status: complete

Milestone 7D introduces the natural-language parser boundary for the API-first trade-capture workflow accepted in ADR-008.

## Delivered Scope

- `TradeCaptureParser` port for parsing user-authored trade language into an editable `TradeCaptureDraft`
- `TradeCaptureParseError` for clear parser failures
- deterministic `FakeTradeCaptureParser` for tests and later API wiring
- LiteLLM-backed parser adapter
- environment-based parser configuration:
  - `TRADING_SYSTEM_LLM_MODEL`
  - `TRADING_SYSTEM_LLM_API_BASE`
- strict extraction prompt that tells the provider not to suggest trades, invent missing values, verify claims, approve plans, create order intents, open positions, or record fills
- JSON response validation and mapping into the Milestone 7C draft contract
- missing and ambiguous fields surfaced through the existing draft validation contract

Docker runtime defaults still point the API container at host Ollama through:

```text
TRADING_SYSTEM_LLM_API_BASE=http://host.docker.internal:11434
TRADING_SYSTEM_LLM_MODEL=ollama_chat/llama3.1
```

Native local runs should set `TRADING_SYSTEM_LLM_API_BASE` to the host Ollama URL, commonly:

```text
http://localhost:11434
```

## Not Included

7D does not implement:

- FastAPI trade-capture endpoints
- frontend trade-capture workspace
- local JSON save workflow
- trade idea, thesis, or plan persistence from parser output
- approval, rule evaluation, order intent, position, fill, broker, recommendation, or claim-verification behavior

## Validation

Validation recorded on 2026-05-02:

- `uv run pytest tests\test_trade_capture_draft.py tests\test_trade_capture_parser.py`: 22 passed
- `uv run pytest tests\test_trade_capture_draft.py tests\test_trade_capture_parser.py tests\test_reference_lookup_service.py tests\test_api_health.py`: 30 passed
- `uv run pytest`: 207 passed

## Next

The next Milestone 7 issue is 7E: FastAPI Trade Capture Service.
