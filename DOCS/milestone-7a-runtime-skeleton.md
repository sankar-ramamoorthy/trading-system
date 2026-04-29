# Milestone 7A Runtime Skeleton

Status: complete

Milestone 7A introduces the first web/API runtime shell for ADR-008.

## Delivered Scope

- FastAPI application entrypoint with `GET /health`
- Vite React TypeScript frontend shell
- frontend health check call to the backend
- Docker Compose stack for `api` and `web`
- backend environment placeholders for future LiteLLM/Ollama parser work
- host Ollama endpoint default: `http://host.docker.internal:11434`

Ollama is intentionally not a Compose service in this slice because it is expected to run on the host.

## Not Included

7A does not implement:

- instrument or playbook lookup
- trade-capture draft schemas
- natural-language parsing
- save workflow
- approval, rule evaluation, order intent, position, fill, or broker workflows

## Run

```powershell
docker compose up --build
```

Then open:

```text
http://localhost:5173
```

The API health endpoint is available at:

```text
http://localhost:8000/health
```

## Native Backend Check

```powershell
uv run uvicorn trading_system.app.api:app --host 0.0.0.0 --port 8000
```

## Validation

```powershell
uv run pytest
```

The frontend can be checked separately from `frontend/` with:

```powershell
npm install
npm run build
```

Closeout validation recorded on 2026-04-29:

- `uv run pytest tests\test_api_health.py`: 1 passed
- `uv run pytest`: 178 passed
- `npm.cmd install`: completed with 0 vulnerabilities
- `npm.cmd run build`: completed successfully
- `docker compose config`: valid
- `docker compose up --build -d`: built and started `api` and `web`
- API health returned `{"status":"ok"}`
- web endpoint returned HTTP 200 at `http://127.0.0.1:5173`

## Next

The next Milestone 7 issue is 7B: Reference Lookup Foundation.
