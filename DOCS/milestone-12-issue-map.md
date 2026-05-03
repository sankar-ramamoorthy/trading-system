# Milestone 12 Issue Map: Paper Execution Hardening

Milestone 12 hardens the simulated paper broker workflow before Alpaca, API, or web execution work. The implementation remains core services plus CLI only.

## Issues

### 12A: Broker Order Query And CLI Listing

Improve local broker-order inspection.

- `BrokerQueryService`
- `list-broker-orders`
- filters for provider, status, position id, and order intent id
- oldest/newest sorting

Status: complete.

### 12B: Broker Order Detail Visibility

Expose linked local metadata without broker secrets.

- `show-broker-order` includes linked fill count and fill ids
- `show-broker-order` includes order-intent status, position state, and open quantity
- `show-position` fill output includes broker-order linkage
- `show-position-timeline` surfaces broker-order ids from lifecycle event details

Status: complete.

### 12C: Simulated Terminal Outcomes

Add local simulated cancellation and rejection behavior.

- `cancel-paper-order`
- `reject-paper-order --reason`
- terminal statuses persist as `canceled` and `rejected`
- cancel/reject only apply to submitted broker orders
- canceled/rejected broker orders cannot be synced into fills
- lifecycle events: `BROKER_ORDER_CANCELED`, `BROKER_ORDER_REJECTED`

Status: complete.

### 12D: Validation And Closeout

Validate the hardening slice and update project status.

- focused broker/query/persistence/CLI tests
- full `uv run pytest`
- update status and roadmap docs with validation results

Status: complete.

## Boundary

Milestone 12 does not add Alpaca, FastAPI broker endpoints, React broker controls, real-money execution, autonomous trading, recommendations, or full order-management-system behavior.

Broker data remains external execution fact. Local JSON remains the source of truth for internal trade records and audit history.

## Validation

Recorded on 2026-05-03:

- `uv run pytest tests\test_broker_execution_service.py tests\test_json_persistence.py tests\test_cli_workflow_commands.py tests\test_cli_retrieval.py`: 85 passed
- `uv run pytest`: 264 passed
