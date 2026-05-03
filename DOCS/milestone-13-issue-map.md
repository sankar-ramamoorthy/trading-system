# Milestone 13 Issue Map: Alpaca Paper Adapter

Milestone 13 adds live Alpaca paper trading behind the accepted broker execution boundary. The implementation remains core services plus CLI only.

## Issues

### 13A: Alpaca Paper Broker Adapter

Add the first external paper broker implementation behind the existing broker port.

- `AlpacaPaperBrokerClient`
- official `alpaca-py` dependency
- paper-only `TradingClient(..., paper=True)`
- vault-first, environment-fallback credentials for `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- local `OrderIntent` mapping to Alpaca market, limit, stop, and stop-limit requests
- Alpaca status mapping into local `BrokerOrderStatus`

Status: complete.

### 13B: CLI Provider Selection And Sync

Expose Alpaca through the existing paper-order CLI commands.

- `submit-paper-order --provider alpaca`
- `sync-paper-order` chooses the broker client from the persisted broker order provider
- simulated sync still uses `--simulated-fill-price`
- Alpaca sync does not require or accept a simulated fill price
- non-filled provider sync updates the local broker order without importing a fill

Status: complete.

### 13C: Validation And Closeout

Validate the Alpaca slice without live network calls in tests.

- fake-client adapter tests for request mapping and status mapping
- service tests for unfilled provider sync without fill import
- CLI tests for Alpaca provider selection and sync
- full test suite

Status: complete.

## Boundary

Milestone 13 does not add real-money execution, FastAPI broker endpoints, React broker controls, browser execution buttons, autonomous trading, broker-position reconciliation, or full order-management-system behavior.

Broker data remains external execution fact. Local JSON remains the source of truth for internal trade records and audit history.

## Validation

Recorded on 2026-05-03:

- `uv run pytest tests\test_alpaca_paper_broker.py tests\test_broker_execution_service.py tests\test_cli_workflow_commands.py`: 44 passed
- `uv run pytest`: 280 passed
