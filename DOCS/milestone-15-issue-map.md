# Milestone 15 Issue Map: Alpaca Read-Only Market Data Provider

Milestone 15 adds Alpaca as a read-only market and options data provider behind the existing market-context boundary. Alpaca provider output is stored only as `MarketContextSnapshot` records and remains separate from Alpaca broker execution.

## Issues

### 15A: Alpaca Daily OHLCV Adapter

Add an Alpaca-backed daily bars adapter behind the existing provider registry.

- `fetch-market-data --provider alpaca`
- Alpaca `StockHistoricalDataClient`
- free-tier `DataFeed.IEX`
- raw daily bars normalized to existing `daily_ohlcv` payload shape
- vault-first, environment-fallback credentials for `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`

Status: complete.

### 15B: Alpaca Options Chain Adapter

Add an Alpaca-backed options chain adapter behind the existing provider registry.

- `fetch-options-chain --provider alpaca`
- Alpaca `OptionHistoricalDataClient`
- free-tier `OptionsFeed.INDICATIVE`
- single-expiration options snapshots normalized to existing `options_chain` payload shape
- contract quote, trade, volume, open interest, implied volatility, and greek fields included when available

Status: complete.

### 15C: CLI And Provider Registry Wiring

Expose Alpaca through existing market-context commands without adding new command surfaces.

- no new CLI commands
- no new feed flags
- yfinance remains the default provider
- no automatic fallback between yfinance, Massive.com, and Alpaca

Status: complete.

## Boundary

Milestone 15 does not add broker submission, broker sync, broker reconciliation, FastAPI or React broker controls, live streaming, scheduled refresh, polling, webhooks, background jobs, recommendations, AI interpretation, generated trade meaning, or trade mutation.

Alpaca market data code remains separate from the Alpaca broker execution adapter. Provider response objects stay inside infrastructure adapters.

## Validation

Recorded on 2026-05-04:

- `uv run pytest tests\test_market_data_provider_registry.py tests\test_cli_market_data_fetch.py tests\test_alpaca_market_data_source.py tests\test_alpaca_options_chain_source.py`: 27 passed
- `uv run pytest`: 305 passed
