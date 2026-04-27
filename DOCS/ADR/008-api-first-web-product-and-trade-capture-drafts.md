---
title: API-First Web Product And Trade Capture Drafts
status: accepted
date: 2026-04-27
tags: [adr, api-first, web-ui, fastapi, trade-capture, trader-language-input, boundaries]
---

# ADR-008: API-First Web Product And Trade Capture Drafts

## Status

Accepted

## Context

The system has proven a local-first manual workflow through the CLI, including `TradeIdea`, `TradeThesis`, `TradePlan`, plan approval, rule evaluation, order intent, position lifecycle, fills, and review.

The CLI remains useful, but recent usage exposed a product-level limitation: the user must currently provide implementation-facing identifiers such as `instrument_id` and `playbook_id`. A trader naturally thinks in symbols, playbook names, thesis language, entry/stop/target notes, evidence, and uncertainty.

Requiring UUIDs or several command invocations makes real trade capture slower than it should be. A viable product needs a user-facing workflow that accepts normal trader language and turns it into editable structured drafts without weakening the existing domain boundaries.

## Decision

The next product direction is an API-first local web product.

The accepted product architecture is:

- add a local FastAPI service boundary over the existing domain and service layers
- use a React/Vite web UI as the intended primary user-facing product surface
- keep the existing Typer CLI as a supported power, debug, admin, and scripting surface
- keep the current local JSON store as the active persistence backend for this stage
- add user-friendly lookup support so workflows can resolve symbols and playbook names instead of requiring UUIDs in user-facing input

The first web workflow is trade capture.

The user should be able to enter normal trader language and receive editable draft sections for:

- `TradeIdea`: what the trade is
- `TradeThesis`: why it might work
- `TradePlan`: how it would be executed

Parsed output is a draft. It must not be persisted until the user explicitly saves.

The first trader-language parser should be introduced behind a parser port with a deterministic or stub implementation first. A future LLM parser may be added behind the same interface without changing the API or persistence workflow.

## Required Behavior

The first API and web workflow must:

- expose workflow behavior through FastAPI rather than shelling out to the CLI
- preserve the existing domain and application services as the source of trade lifecycle behavior
- let the UI work with symbols and playbook names or slugs instead of user-entered UUIDs
- parse raw trade-capture text into editable draft fields
- surface missing or ambiguous fields clearly
- require explicit user confirmation before saving
- create persisted `TradeIdea`, `TradeThesis`, and `TradePlan` records only through existing service boundaries
- keep plan approval, rule evaluation, order intent creation, position opening, fill recording, and review as separate workflows

## Not Allowed

The first API-first web product slice must not add:

- trade suggestions
- system-generated buy, stop, or target recommendations
- thesis claim verification, such as checking whether a symbol is holding the 20DMA
- automatic plan approval
- order intent creation from the capture screen
- position opening from the capture screen
- fill recording from the capture screen
- broker integration
- Postgres migration
- production auth, cloud deployment, or multi-user hosting
- replacement or removal of the CLI

## Rationale

An API-first boundary lets the product grow beyond CLI ergonomics without discarding the working domain model.

FastAPI provides a clear local service surface for web workflows and future clients. React/Vite is appropriate for the first primary UI because trade capture needs editable sections, missing-field indicators, and review-before-save behavior.

Keeping the CLI avoids losing a useful tool for scripting, diagnostics, and regression workflows.

Keeping local JSON persistence avoids coupling this product step to a storage migration. The value of this slice is product usability and service boundaries, not database replacement.

Using a parser port allows the system to start with deterministic extraction or stubs while preserving the later option to add LLM-backed parsing. This keeps natural-language input separate from persistence, approval, and execution behavior.

## Consequences

### Positive

- moves the product toward trader-native workflows
- avoids exposing implementation identifiers as primary user input
- preserves existing domain boundaries and tests
- provides a service boundary for web UI and future clients
- keeps parsed text auditable through explicit draft review and save
- allows LLM parsing later without making it foundational to the first API/UI slice

### Trade-Offs

- introduces a new runtime surface and dependency set
- adds API schemas and frontend state as contracts to maintain
- requires explicit lookup semantics for instruments and playbooks
- requires careful UI design so parser output does not appear more certain than it is
- adds product complexity before broker integration or cloud deployment

These trade-offs are accepted because repeated trade capture needs to feel natural before the system can become a viable daily workflow product.

## Deferred

Future claim verification belongs in a context-intelligence or thesis-verification layer. It should decompose claims, attach evidence, include confidence and data timestamps, and remain advisory.

Future system-generated entry, stop, or target suggestions belong in a separate decision-support boundary with explicit human acceptance. They should not be introduced as part of the first parser or capture workflow.

Any later move to Postgres, production deployment, broker integration, generated recommendations, or execution automation should be planned separately and may require additional ADRs.
