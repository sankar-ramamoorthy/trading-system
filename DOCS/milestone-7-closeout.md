---
title: Milestone 7 API-First Trade Capture Workspace Closeout
status: complete
date: 2026-05-02
tags: [milestone-7, trade-capture, api, react, fastapi, docker, closeout, trading-system]
---

# Milestone 7 API-First Trade Capture Workspace Closeout

## Summary

Milestone 7 is complete.

The system now has a local web product for trade capture. A Docker-compose stack runs the FastAPI backend and the React/Vite trade-capture UI together. A trader enters raw trade language, parses it through a local or cloud LLM, edits the resulting draft, and saves the confirmed draft as linked `TradeIdea`, `TradeThesis`, and `TradePlan` records in the local JSON store.

The records created through the web interface are identical to records created through the CLI workflow. They can be inspected, filtered, and reviewed using all existing CLI commands.

## Completed Slices

- Milestone 7A: Docker Compose runtime with FastAPI health endpoint and Vite frontend shell.
- Milestone 7B: Seeded instrument and playbook reference lookup through service and API boundaries.
- Milestone 7C: Editable `TradeIdeaDraft`, `TradeThesisDraft`, and `TradePlanDraft` draft contracts with required fields, optional fields, missing-field reporting, and save-readiness checks.
- Milestone 7D: `TradeCaptureParser` port, `TradeCaptureParseError`, deterministic fake parser, and LiteLLM-backed adapter with strict extraction prompt and JSON validation.
- Milestone 7E: `POST /trade-capture/parse`, `POST /trade-capture/save`, and `GET /trade-capture/saved/{trade_plan_id}` over existing services and repositories.
- Milestone 7F: React/Vite trade-capture workspace with raw input, parse action, editable draft sections, field-level issue display, explicit save, and saved-result summary.
- Milestone 7G: End-to-end Docker/API acceptance — parse, edit, save, and local JSON persistence all validated; LLM provider switched to Groq and parser hardened for model output variance.

## Implemented Workflow

### Prerequisites

Create a `.env` file in the application repo root with LLM credentials:

```text
TRADING_SYSTEM_LLM_MODEL=groq/qwen/qwen3-32b
TRADING_SYSTEM_LLM_API_BASE=https://api.groq.com/openai/v1
GROQ_API_KEY=<your-groq-api-key>
```

`TRADING_SYSTEM_LLM_API_BASE` is optional for Groq — the default value in docker-compose points to the local Ollama host. Set it explicitly to override.

### Start the Stack

```powershell
docker compose up --build
```

- API: `http://localhost:8000`
- UI: `http://localhost:5173`

### Trade Capture Workflow

1. Open `http://localhost:5173` in a browser.
2. Enter a raw trade note in the input field.
3. Click **Parse** — the draft sections populate with extracted `TradeIdea`, `TradeThesis`, and `TradePlan` fields.
4. Review and edit any missing or ambiguous fields surfaced by the validator.
5. Click **Save** — the system creates linked records in the local JSON store.
6. The saved-result summary shows the generated IDs.

The saved records are immediately accessible through the CLI:

```powershell
uv run trading-system list-trade-ideas
uv run trading-system show-trade-plan <trade-plan-id>
```

### LLM Configuration

The parser routes through LiteLLM. Any model accessible via LiteLLM is supported:

- **Groq** (validated): `groq/qwen/qwen3-32b` with `GROQ_API_KEY`
- **Ollama** (local): `ollama_chat/<model-name>` with `TRADING_SYSTEM_LLM_API_BASE=http://host.docker.internal:11434`
- Any other LiteLLM-supported provider via `TRADING_SYSTEM_LLM_MODEL` and `TRADING_SYSTEM_LLM_API_BASE`

Do not store API keys in committed files. Use `.env` which is listed in `.gitignore`.

## Boundaries Preserved

- no broker integration
- no automated execution
- no plan approval from the capture screen
- no rule evaluation from the capture screen
- no order intent creation from the capture screen
- no position opening or fill recording from the capture screen
- no generated trade recommendations
- no claim verification
- no production auth or multi-user access
- no cloud deployment
- no Postgres migration
- no AI-generated advice; the parser extracts only user-authored content
- API keys are not stored in snapshots, logs, docs examples, tests, or committed files
- local encrypted key storage remains a future ADR candidate

## Validation

Final Milestone 7 validation passed on 2026-05-02:

```powershell
uv run pytest
```

Result: 216 full-suite tests passed.

```powershell
npm.cmd run build
```

Result: frontend production build passed.

```powershell
docker compose up --build
curl http://localhost:8000/health
```

Result: both containers healthy; API returned `{"status": "ok"}`.

End-to-end API validation (7G acceptance):

- `POST /trade-capture/parse` extracted fields and surfaced issues correctly.
- `POST /trade-capture/save` created linked `TradeIdea`, `TradeThesis`, and `TradePlan` records.
- `GET /trade-capture/saved/{trade_plan_id}` retrieved the saved result summary.
- Local JSON store confirmed all three linked records with `approval_state: draft`.
- All error states verified: empty input, missing required fields, ambiguous fields, unknown symbol, unknown plan ID.

## Follow-Up

Milestone 7 is closed. Milestone 8 direction is outcome-level and will be defined when a narrow implementation slice is ready. See `DOCS/product-roadmap.md` for the current high-level trajectory.

Open questions carried forward:

- Local encrypted API-key storage: a possible narrow local-operations slice before a full ADR or milestone.
- Reusable local secret-vault library: library-first design, not yet scoped as a milestone.

Do not expand the trade-capture screen into approval, rule evaluation, order intent creation, position management, or any execution path without a new explicit issue or ADR.

## Related Documents

- [ADR-008: API-First Web Product and Trade Capture Drafts](ADR/008-api-first-web-product-and-trade-capture-drafts.md)
- [Milestone 7 Issue Map](milestone-7-issue-map.md)
- [Milestone 7A: Runtime Skeleton](milestone-7a-runtime-skeleton.md)
- [Milestone 7B: Reference Lookup Foundation](milestone-7b-reference-lookup-foundation.md)
- [Milestone 7C: Trade Capture Draft Contract](milestone-7c-trade-capture-draft-contract.md)
- [Milestone 7D: Natural-Language Parser Boundary](milestone-7d-natural-language-parser-boundary.md)
- [Milestone 7E: FastAPI Trade Capture Service](milestone-7e-fastapi-trade-capture-service.md)
- [Milestone 7F: React Trade Capture Workspace](milestone-7f-react-trade-capture-workspace.md)
