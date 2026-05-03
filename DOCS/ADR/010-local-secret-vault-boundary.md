---
title: Local Secret Vault Boundary
status: accepted
date: 2026-05-03
tags: [adr, secrets, credentials, key-vault, milestone-10]
---

# ADR-010: Local Secret Vault Boundary

## Status

Accepted

## Context

The system is a local-first trading workflow with CLI and web entry points. Milestones 6 through 9 introduced external provider access, LiteLLM-backed trade capture parsing, Docker runtime support, and browser-based planning workflows.

The current local credential pattern still depends on plain environment variables and `.env` loading for CLI use. That was acceptable for early local development, but it should not remain the preferred long-term way to store provider API keys as the system moves toward more integrations.

Current credential and configuration examples include:

- `MASSIVE_API_KEY` for Massive.com market data and options data
- `TRADING_SYSTEM_LLM_MODEL` and `TRADING_SYSTEM_LLM_API_BASE` for LiteLLM parser configuration
- `TRADING_SYSTEM_STORE_PATH` for local JSON persistence location

Only secret values should move behind a vault boundary. Ordinary runtime configuration, model names, URLs, and store paths should remain environment or configuration values unless a later ADR changes that boundary.

The project needs a credential boundary before adding more provider credentials or future broker-paper-trading credentials.

## Decision

Milestone 10 accepts a local encrypted secret vault boundary for CLI workflows.

The first implementation direction should introduce a small provider-agnostic `local_secret_vault` library boundary responsible for storing, retrieving, deleting, listing, and rotating local secrets.

The accepted storage model is:

- encrypted vault file at `.trading-system/keys.enc`
- encrypted secret values only, never plaintext values
- master key stored through the operating system keychain
- Fernet-style symmetric encryption for the first implementation

CLI secret resolution should use this precedence:

1. encrypted local vault
2. environment variable fallback
3. clear missing-secret error

Environment variables and `.env` remain supported for Docker, CI, non-interactive runtime use, and fallback compatibility. They are no longer the preferred CLI storage mechanism for secret values.

The initial secret names expected to use the vault boundary are provider API keys such as:

- `MASSIVE_API_KEY`
- future LLM provider keys such as `GROQ_API_KEY` or `OPENAI_API_KEY`

Non-secret runtime settings such as `TRADING_SYSTEM_LLM_MODEL`, `TRADING_SYSTEM_LLM_API_BASE`, and `TRADING_SYSTEM_STORE_PATH` should remain outside the vault in the first implementation.

## Required Behavior

The first implementation slice after this ADR should provide CLI commands for:

- `set-secret`
- `list-secrets`
- `delete-secret`
- `rotate-master-key`

`list-secrets` must show secret names or metadata only. It must never print secret values.

Provider adapters and parser/provider setup should eventually receive secret values through an explicit resolver instead of directly reading `os.environ`.

Secrets must stay out of:

- snapshots
- logs
- committed files
- docs examples
- test fixtures
- API responses

Vault errors should be clear and local-actionable, including missing secret, missing or unavailable keychain, unreadable vault, invalid vault, and decrypt failure.

## Not Allowed

Milestone 10 must not add:

- cloud secret management
- team or shared vault support
- browser-based secret entry
- production authentication or authorization
- key synchronization across machines
- remote secret backup
- live broker credentials for real-money execution

The vault must not become a general configuration database. It is for secret values only.

## Rationale

A local vault improves credential hygiene before the project adds more provider or broker-adjacent integrations.

Keeping the vault provider-agnostic avoids coupling credential storage to Massive.com, LiteLLM, Groq, OpenAI, or any future broker boundary. Keeping resolution separate from provider adapters preserves testability and lets adapters continue to operate with injected or resolved values.

Preserving environment fallback keeps Docker and non-interactive workflows practical. Docker Compose can continue using `.env`, while local CLI workflows can move to encrypted storage.

Separating secret values from ordinary runtime configuration avoids encrypting harmless settings and keeps local operations understandable.

## Consequences

### Positive

- reduces reliance on plain-text `.env` for CLI API keys
- creates a single credential-resolution boundary before future integrations
- keeps provider adapters from owning secret lookup policy
- preserves Docker and CI compatibility through environment fallback
- records the security boundary before implementation

### Trade-Offs

- adds a future dependency on cryptography and OS keychain behavior
- introduces platform-specific failure modes around keychain availability
- requires migration guidance for users with existing `.env` keys
- adds operational commands that must avoid printing or logging secret values

These trade-offs are accepted because the system is moving toward more integrations and should establish local credential hygiene before paper-trading or broker-boundary work.

## Follow-Up

The next implementation issue should add the local vault library boundary, CLI commands, tests, and documentation.

The first code slice should update Massive.com secret resolution to use the vault-first resolver with environment fallback. Later slices can route LLM provider API keys through the same boundary when provider-specific keys are introduced.
