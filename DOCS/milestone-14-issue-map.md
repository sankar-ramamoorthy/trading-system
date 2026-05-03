# Milestone 14 Issue Map: Broker Reconciliation And Status Sync

Milestone 14 adds explicit CLI-only broker reconciliation after the Alpaca paper adapter. Local `BrokerOrder`, `Fill`, and `Position` records remain canonical for internal audit; Alpaca facts are external execution facts used for explicit sync and mismatch reporting.

## Issues

### 14A: Broker Order Snapshots

Add provider-side broker order snapshots behind the existing broker port.

- `BrokerOrderSnapshot`
- provider order id, mapped local status, updated time, symbol, side, quantity, and optional fill price
- Alpaca `get_orders(GetOrdersRequest(status=QueryOrderStatus.ALL))`
- provider response objects stay inside infrastructure

Status: complete.

### 14B: Broker Reconciliation Service

Add explicit reconciliation workflows for local broker orders.

- batch sync local submitted broker orders for a provider
- import fills idempotently through the existing broker fill path
- update local broker order status for remote submitted, canceled, rejected, and filled states
- report local terminal status and fill mismatches without deleting or redefining local records
- report missing remote and broker-only remote records

Status: complete.

### 14C: CLI Reconciliation Commands

Expose reconciliation through local operator commands only.

- `sync-broker-orders --provider alpaca`
- `reconcile-broker-orders --provider alpaca`
- per-order sync output for batch sync
- reconciliation counts for matched, updated, missing-remote, broker-only, status-mismatch, and fill-mismatch records

Status: complete.

### 14D: Audit Events And Validation

Record explicit local audit events for broker sync and mismatch reporting.

- `BROKER_ORDER_SYNCED` for non-fill broker status checks and updates
- `BROKER_ORDER_RECONCILIATION_MISMATCH` for local broker-order mismatches
- `BROKER_ORDER_FILLED` remains the fill-import event

Status: complete.

## Boundary

Milestone 14 does not add real-money execution, FastAPI broker endpoints, React broker controls, browser execution buttons, broker positions as canonical local positions, scheduled sync, polling, streaming, webhooks, background jobs, or automatic repair of `Position`, `OrderIntent`, or `Fill` records beyond the existing explicit fill import path.

Broker-only remote orders are report-only in Milestone 14. The system does not create local orders from broker-only records.

## Validation

Recorded on 2026-05-03:

- `uv run pytest tests\test_alpaca_paper_broker.py tests\test_broker_reconciliation_service.py tests\test_broker_execution_service.py tests\test_cli_workflow_commands.py`: 51 passed
- `uv run pytest`: 287 passed
