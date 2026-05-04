# Milestone 16 Issue Map: Finqual Fundamentals Provider

Milestone 16 adds Finqual as a read-only fundamentals and ownership provider behind the existing market-context boundary. Finqual provider output is stored only as `MarketContextSnapshot` records and remains advisory external context.

## Issues

### 16A: Finqual Financial Statement Adapter

Add Finqual-backed financial statement imports through explicit CLI commands.

Completed direction:

- `fetch-financial-statement --provider finqual`
- `/income-statement`, `/balance-sheet`, and `/cash-flow`
- annual or quarterly statement selection
- vault-first, environment-fallback resolution for `FINQUAL_API_KEY`
- `context_type = financial_statement`

### 16B: Finqual Insider Transactions Adapter

Add recent insider transaction imports for one ticker.

Completed direction:

- `fetch-insider-transactions --provider finqual`
- ticker and period query parameters
- `context_type = insider_transactions`

### 16C: Finqual 13F Holdings Adapter

Add recent 13F holdings imports for one CIK.

Completed direction:

- `fetch-13f --provider finqual`
- CIK and period query parameters
- explicit `--instrument-id` or target link required because the app has no CIK reference registry
- `context_type = institutional_holdings_13f`

## Boundary

Milestone 16 does not add automatic provider fallback, scheduled refresh, streaming, portfolio analytics, automated scoring, recommendations, AI interpretation, generated trade meaning, or trade mutation.

Finqual response objects remain inside infrastructure adapters. The stored payload keeps provider JSON under `data`; Finqual does not define canonical trade meaning.

## Validation

Recorded on 2026-05-04:

- `uv run pytest tests\test_finqual_context_sources.py tests\test_finqual_provider_registry.py tests\test_cli_finqual_fetch.py`: 18 passed
- `uv run pytest`: 323 passed
