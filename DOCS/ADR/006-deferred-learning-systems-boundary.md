---
title: Deferred Learning Systems Boundary
status: accepted
date: 2026-04-26
tags: [adr, learning-systems, ai, reinforcement-learning, boundaries]
---

# ADR-006: Deferred Learning Systems Boundary

## Status

Accepted

## Context

The project has a strong long-term interest in review-driven learning, simulator practice, AI-assisted insight, and eventually reinforcement-learning-style policy simulation.

The current system is not ready for AI or RL. It must first produce reliable ground truth through stable manual workflows, structured trade records, consistent review data, and clear labels for decisions and outcomes.

Introducing learning systems too early would blur the boundary between trader-authored intent, external context, and generated suggestions. It would also risk drawing conclusions from sparse or inconsistent data.

## Decision

AI, ML, and reinforcement-learning systems are explicitly deferred beyond the accepted Milestones 3 through 5 roadmap.

The current repository remains:

- deterministic
- local-first
- human-driven
- auditable
- focused on structured ground-truth capture

Learning systems may be reconsidered only after the project has:

- stable manual workflows
- consistent completed-trade reviews
- reliable setup, decision, mistake, and outcome labels
- enough completed trades or scenarios for meaningful analysis
- explicit success and failure definitions
- a new accepted roadmap slice for learning-system work

The guiding rule is:

```text
No intelligence before truth.
```

## Allowed Before Learning Systems

The project may still implement non-AI foundations that make later learning possible:

- structured review tags
- narrow journal-grade reports
- local exports
- scenario labels, if introduced through a future simulator milestone
- deterministic or statistical summaries

These features must remain explainable and auditable.

## Not Allowed Yet

The project should not implement:

- AI-generated trade decisions
- AI-generated execution instructions
- AI-generated review conclusions treated as canonical
- reinforcement learning
- autonomous strategy optimization
- broker automation driven by learned policies
- black-box decision scoring

## Rationale

The system's first responsibility is to capture what was planned, what happened, and what was learned.

Learning systems depend on clean state representation, consistent labels, stable reward definitions, and enough examples. Without those foundations, AI or RL would produce misleading conclusions and add complexity before the core workflow has proven itself.

Keeping learning systems deferred protects the architecture from premature product drift.

## Consequences

### Positive

- preserves the manual and auditable workflow
- keeps Milestones 4 and 5 focused
- protects the source-of-truth boundary
- allows future learning systems to use cleaner data

### Trade-Offs

- no short-term AI coaching or generated review content
- no RL experimentation in the main application roadmap yet
- simulator and policy-testing ideas require later planning

These trade-offs are accepted to keep the project grounded in reliable data first.

## Companion Roadmap

The evolving near-term and long-term roadmap lives in:

- [Product Roadmap](../product-roadmap.md)

This ADR records the durable boundary. The roadmap records sequencing and may evolve as milestones complete.
