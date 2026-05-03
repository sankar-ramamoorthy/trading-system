# Milestone 8 Issue Map: Options Chain Ingestion

Milestone 8 adds options chain data as the first market data depth extension. Options context gives traders strike-level visibility — implied volatility, open interest, bid/ask — to support position sizing and risk assessment before entering a trade.

## Issues

### 8A: yfinance Options Chain

Add `YFinanceOptionsChainImportSource` and wire it into the provider registry and CLI.

- `src/trading_system/infrastructure/yfinance/options_chain_source.py`
- `src/trading_system/infrastructure/market_data_providers.py` — `create_options_chain_source()`
- `src/trading_system/app/cli.py` — `fetch-options-chain` command
- `tests/test_yfinance_options_chain_source.py`

Status: complete.

### 8B: Massive.com Options Chain

Add `MassiveOptionsChainImportSource` behind the same registry method and CLI command.

- `src/trading_system/infrastructure/massive/options_chain_source.py`
- `tests/test_massive_options_chain_source.py`

Status: complete.

Note: Massive.com options snapshot data (`list_snapshot_options_chain`) requires a paid plan. The adapter is implemented and tested; live execution requires a paid Massive.com subscription. The free tier returns `NOT_AUTHORIZED` and the CLI surfaces a clear upgrade message.

### 8C: Milestone 8 Closeout

Docs, STATUS, README, knowledge-base updates.

Status: complete.

## Boundary

Milestone 8 does not add live options quotes, options pricing models, greeks calculation, options strategy construction, multi-leg position support, or order execution of any kind.

## Command Reference

```powershell
# Fetch options chain for a specific expiry
uv run trading-system fetch-options-chain AAPL --expiry 2026-05-22 --provider yfinance
uv run trading-system fetch-options-chain AAPL --expiry 2026-05-22 --provider massive

# Link to a trade plan
uv run trading-system fetch-options-chain AAPL --expiry 2026-05-22 --provider yfinance --target-type trade-plan --target-id <plan-id>

# Inspect the stored snapshot
uv run trading-system show-context <snapshot-id>
uv run trading-system list-context --context-type options_chain
```

The snapshot is stored as `context_type: options_chain` and is linkable to plans, positions, or reviews — the same attachment model as daily OHLCV.
