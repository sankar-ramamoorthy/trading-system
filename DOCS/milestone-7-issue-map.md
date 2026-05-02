# Milestone 7 Issue Map: API-First Trade Capture Workspace

Milestone 7 delivers the first local web product workflow from ADR-008.

The milestone is split into narrow issues so the runtime, lookup, draft contract, parser, API, UI, save workflow, and closeout each have clear boundaries.

## Issues

### 7A: Dockerized Runtime Foundation

Create the local runtime shell:

- Docker Compose for backend and frontend
- FastAPI health endpoint
- Vite React TypeScript frontend shell
- frontend-to-backend health check
- host Ollama configuration placeholders

Status: complete.

Ollama runs on the host for now. 7A does not implement trade capture.

### 7B: Reference Lookup Foundation

Add user-facing instrument and playbook lookup so web/API workflows can use symbols and playbook slugs instead of UUIDs.

Status: complete.

### 7C: Trade Capture Draft Contract

Define editable draft contracts for `TradeIdea`, `TradeThesis`, and `TradePlan`, including required fields, optional fields, and missing or ambiguous field reporting.

Status: complete.

### 7D: Natural-Language Parser Boundary

Add the LLM-first parser boundary through LiteLLM, with host Ollama as the first local runtime.

The parser extracts only user-authored content. It must not suggest trades, invent missing levels, verify claims, approve plans, create order intents, open positions, or record fills.

### 7E: FastAPI Trade Capture Service

Expose lookup, parse, save, and saved-result retrieval through FastAPI over existing services and repositories.

The API must not shell out to the CLI.

### 7F: React/Vite Trade Capture Workspace

Build the focused capture screen with raw trader-language input, parse action, editable Idea/Thesis/Plan sections, missing-field indicators, explicit save, and saved result summary.

### 7G: End-to-End Save Workflow

Wire parse, edit, and save through local JSON persistence so explicit save creates linked `TradeIdea`, `TradeThesis`, and `TradePlan` records.

### 7H: Milestone Closeout

Close the milestone with tests, documentation, roadmap/status updates, and final validation.

## Boundary

Milestone 7 does not add broker integration, order execution, plan approval from the capture screen, generated trade recommendations, claim verification, production auth, cloud deployment, or a Postgres migration.
