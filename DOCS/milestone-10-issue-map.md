# Milestone 10 Issue Map: Secure Credentials

Milestone 10 replaces plain-text `.env` API key reliance for CLI workflows with a local encrypted secret vault while preserving environment-variable fallback for Docker and non-interactive runs.

## Issues

### 10A: Local Secret Vault Boundary

Record the credential architecture before implementation.

- `DOCS/ADR/010-local-secret-vault-boundary.md`
- Vault-first, environment-fallback resolution
- Encrypted local vault file at `.trading-system/keys.enc`
- OS keychain-backed master key
- Secret values only, not ordinary runtime configuration

Status: complete.

### 10B: Vault Library And CLI Commands

Add the first local encrypted vault implementation and operator commands.

- `local_secret_vault` infrastructure boundary
- Fernet-encrypted vault payloads
- OS keychain master-key storage through `keyring`
- CLI commands: `set-secret`, `list-secrets`, `delete-secret`, `rotate-master-key`
- Metadata-only listing; secret values are never printed

Status: complete.

### 10C: Massive.com Secret Resolution

Move Massive.com provider credential lookup behind vault-first resolution.

- Massive daily OHLCV and options chain adapters resolve `MASSIVE_API_KEY` through the local vault first
- Environment fallback remains supported for Docker, CI, and existing `.env` workflows
- Missing credentials still fail clearly before storing context snapshots

Status: complete.

## Boundary

Milestone 10 does not add cloud secret management, team/shared vaults, browser secret entry, production authentication or authorization, key synchronization, remote backup, or live broker credentials for real-money execution.

The vault is not a general configuration database. Non-secret settings such as model names, API-base URLs, and store paths remain environment/config values.

## Command Reference

```powershell
uv run trading-system set-secret MASSIVE_API_KEY
uv run trading-system list-secrets
uv run trading-system delete-secret MASSIVE_API_KEY
uv run trading-system rotate-master-key
```

`set-secret` prompts for the value and confirmation. `list-secrets` shows names and update timestamps only.

## Validation

Recorded on 2026-05-03:

- `uv run pytest tests\test_local_secret_vault.py tests\test_cli_secrets.py tests\test_massive_market_data_source.py tests\test_massive_options_chain_source.py tests\test_cli_market_data_fetch.py`: 30 passed
- `uv run pytest`: 246 passed
