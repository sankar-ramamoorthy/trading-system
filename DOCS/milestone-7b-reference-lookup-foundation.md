# Milestone 7B Reference Lookup Foundation

Status: complete

Milestone 7B adds the first user-facing reference lookup foundation for the API-first trade-capture workflow.

## Delivered Scope

- `Playbook` domain reference entity
- read-only reference-data repository port
- seeded local reference repository for instruments and playbooks
- reference lookup service for symbol and playbook slug resolution
- FastAPI reference endpoints:
  - `GET /reference/instruments`
  - `GET /reference/instruments/{symbol}`
  - `GET /reference/playbooks`
  - `GET /reference/playbooks/{slug}`
- frontend runtime shell now displays instrument and playbook reference counts

## Seeded References

Seeded instruments:

- `AAPL`
- `MSFT`
- `NVDA`
- `SPY`
- `QQQ`

Seeded playbooks:

- `pullback-to-trend`
- `breakout-continuation`
- `failed-breakdown`

The API still returns internal IDs because later save workflows need them after lookup resolution. User-facing workflows should use symbols and playbook slugs as input.

## Not Included

7B does not implement:

- instrument or playbook management screens
- user-editable reference data
- trade-capture draft schemas
- natural-language parsing
- save workflow
- approval, execution, position, fill, broker, or recommendation behavior

## Validation

Validation recorded on 2026-04-29:

- `uv run pytest tests\test_api_health.py tests\test_reference_lookup_service.py`: 8 passed
- `uv run pytest`: 185 passed
- `npm.cmd run build`: completed successfully

## Next

The next Milestone 7 issue is 7C: Trade Capture Draft Contract.
