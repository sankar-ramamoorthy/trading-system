---
id: ADR-003
title: Hybrid Development Strategy with Docker for Infrastructure and Optional Full Containerization Later
status: accepted
date: 2026-04-18
deciders: [owner]
tags: [development, deployment, docker, uv, fastapi, postgres]
---

# Context

The system will be developed initially on a Windows laptop and later likely on a Mac mini.

The current toolchain and preferences include:

- Python
- `uv`
- `pyproject.toml`
- FastAPI
- Postgres
- Docker / Docker Compose

There is already familiarity and comfort with Docker-based development.

However, the system is still in an early design and architecture phase, and the primary risks at this stage are:

- poor domain modeling
- premature architectural complexity
- slow feedback during testing
- development friction caused by infrastructure choices overshadowing core design work

Docker is useful for reproducibility and isolation, but can also introduce extra constraints during rapid iteration and exploratory testing.

---

# Decision

We will adopt a **hybrid development strategy**.

## Default development mode

During early development, the default approach will be:

- run the Python application directly in a local `uv`-managed environment
- run Postgres in Docker
- keep the application code independent of container-specific assumptions

This gives us:

- fast local iteration
- reduced container-related friction during testing
- a stable and isolated database environment
- an easier transition across development machines

---

## Containerization policy

We will still maintain container support from the beginning:

- a `Dockerfile`
- a `docker-compose.yml`
- environment-variable-based configuration

However, full application containerization will be considered **available but not mandatory** during early development.

---

## Future deployment mode

Once the architecture and workflows stabilize, the system may move to:

- app container
- postgres container
- optional worker/scheduler container

This future topology remains part of the same **modular monolith**, not a microservices architecture.

---

# Decision Details

## Early-phase runtime model

+---------------------------+
| Host Machine              |
|                           |
|  +---------------------+  |
|  | uv-managed app      |  |
|  | FastAPI / scripts   |  |
|  +---------------------+  |
|                           |
|  +---------------------+  |
|  | Docker: Postgres    |  |
|  +---------------------+  |
+---------------------------+

## Later runtime option

+---------------------------+
| Docker Compose            |
|                           |
|  +---------------------+  |
|  | app                 |  |
|  +---------------------+  |
|                           |
|  +---------------------+  |
|  | postgres            |  |
|  +---------------------+  |
|                           |
|  +---------------------+  |
|  | worker (optional)   |  |
|  +---------------------+  |
+---------------------------+

---

# Rationale

## Why not full Docker by default right now?

Because the project is still in a phase where rapid iteration matters more than deployment symmetry.

The main value now is:

* refining the domain model
* validating boundaries
* testing workflows
* changing assumptions quickly

Full containerization can slow this down by adding:

* rebuild loops
* volume-mount quirks
* path and networking friction
* extra debugging layers

These are acceptable later, but not necessary as the default inner development loop.

---

## Why still keep Docker in the picture?

Because it provides clear benefits:

* isolated infrastructure
* reproducible database setup
* future deployment path
* easier transition across machines
* cleaner environment parity later

Using Docker for Postgres now gives most of the benefit with less friction than containerizing everything immediately.

---

## Why not avoid Docker entirely?

Because doing so would discard useful operational discipline and make the later transition to a more reproducible setup less smooth.

The goal is not to reject Docker.
The goal is to avoid becoming unnecessarily dependent on it during the earliest stages of system construction.

---

# Consequences

## Positive

* faster inner development loop
* easier debugging of application logic
* reduced early infrastructure overhead
* stable and isolated database setup
* smooth path toward later full containerization
* works well across Windows and future macOS development

## Negative

* local and containerized app execution may diverge slightly if not kept aligned
* two supported development modes require discipline in configuration
* some environment issues may surface only when running the full containerized stack

---

# Required Constraints

To support this hybrid model, the system must follow these rules:

## 1. Configuration must be environment-driven

All infrastructure endpoints must be configured through environment variables.

Examples:

* database connection string
* external API keys
* broker credentials
* service URLs

No hardcoded host-specific assumptions are allowed.

---

## 2. Application code must remain container-agnostic

The codebase must not assume:

* Docker-specific paths
* Docker-only networking names
* container-only startup order

The app should run correctly:

* locally via `uv`
* inside a container
* later in a multi-container setup

---

## 3. Infrastructure concerns must remain separate from domain concerns

The choice to run locally or in Docker must not affect:

* domain model
* business rules
* context intelligence logic
* trade lifecycle logic

---

## 4. Full containerization remains an operational option, not a design dependency

We support containerization as a deployment/runtime choice.
We do not allow it to distort the internal architecture.

---

# Alternatives Considered

## 1. Full Docker-first development

Rejected as default.

Reasons:

* slower iteration
* unnecessary friction during early modeling and testing
* more moving parts than needed for current stage

## 2. No Docker at all

Rejected.

Reasons:

* weaker reproducibility
* less convenient infrastructure setup
* poorer long-term transition path

## 3. Separate microservices from the beginning

Rejected.

Reasons:

* premature complexity
* not justified by current scope
* would confuse deployment boundaries with domain boundaries

---

# Operational Notes

## Recommended early workflow

* run Postgres via Docker Compose
* run app locally via `uv`
* run tests locally by default
* periodically verify that the app still works in containerized form

## Recommended later workflow

* move app and worker into containers when:

  * architecture is stable
  * scheduled jobs become important
  * reproducibility matters more
  * deployment topology becomes more permanent

---

# Follow-ups

* Define project layout and runtime entry points
* Standardize environment variable strategy
* Add a root-level development guide
* Add a container strategy section to the system blueprint

