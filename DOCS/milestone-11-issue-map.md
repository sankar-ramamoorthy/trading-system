# Milestone 11 Issue Map: Broker Boundary And Simulated Paper Execution

Milestone 11 introduces a broker execution boundary without live broker calls. The implementation is core services plus CLI only.

## Issues

### 11A: Broker Execution Boundary ADR

Record the broker execution boundary before implementation.

- `DOCS/ADR/011-broker-execution-boundary.md`
- Provider-agnostic broker port
- Paper-only first slice
- Reserved future Alpaca secret names: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`

Status: complete.

### 11B: Broker Order Domain And Persistence Boundary

Add local broker-order records while preserving local JSON as the internal source of truth.

- `BrokerOrder` domain record
- `BrokerOrderRepository` protocol
- JSON and in-memory broker-order repositories
- `broker_orders` JSON collection
- optional `Fill.broker_order_id`
- backward-compatible loading for older fill records

Status: complete.

### 11C: Simulated Paper Broker Adapter And Execution Service

Add the first broker port implementation without network calls.

- `BrokerClient` port
- `SimulatedPaperBrokerClient`
- `BrokerExecutionService.submit_paper_order`
- `BrokerExecutionService.sync_paper_order`
- idempotent broker-fill import
- lifecycle events: `BROKER_ORDER_SUBMITTED`, `BROKER_ORDER_FILLED`

Status: complete.

### 11D: CLI Commands

Expose the broker boundary through local operator commands only.

- `submit-paper-order <order-intent-id> --position-id <position-id> --provider simulated`
- `sync-paper-order <broker-order-id> --simulated-fill-price <price>`
- `show-broker-order <broker-order-id>`

Status: complete.

### 11E: Closeout Validation

Validate the broker slice and update project status after test execution.

- focused broker/order-intent/fill/persistence/CLI tests
- full `uv run pytest`
- update status docs with recorded results

Status: complete.

## Boundary

Milestone 11 does not add FastAPI broker endpoints, React broker controls, live Alpaca paper submission, real-money execution, autonomous trading, recommendations, or full OMS behavior.

Future Alpaca work should use the local vault-first, environment-fallback secret resolution pattern for `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`.

## Validation

Recorded on 2026-05-03:

- `uv run pytest tests\test_broker_execution_service.py tests\test_json_persistence.py tests\test_cli_workflow_commands.py tests\test_manual_fill_recording.py tests\test_order_intent_workflow.py`: 71 passed
- `uv run pytest`: 257 passed
