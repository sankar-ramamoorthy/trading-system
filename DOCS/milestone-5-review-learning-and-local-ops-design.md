---
title: Milestone 5 Review Learning And Local Operations Design
status: accepted-for-roadmap
date: 2026-04-24
tags: [milestone-5, review, reporting, local-ops, design, trading-system]
---

# Milestone 5 Review, Learning, And Local Operations Design

## Purpose

Milestone 5 expands the value of completed trades through better review structure, narrow reporting, export support, and practical local operations.

The purpose is to improve learning quality and operational reliability while keeping the system local-first, explicit, and audit-friendly.

## Review, Report, And Export Scope

Milestone 5 may include:

- review tagging and categorization
- filtering and retrieval of reviews by narrow criteria
- journal-grade summaries or exports for completed trades
- local export formats that support inspection, backup, or offline analysis

This milestone should help the trader answer questions such as what was learned, which patterns repeat, and which completed trades match a narrow filter.

## First Implementation Slice

The first Milestone 5 slice is review tagging and filtering.

This slice adds creation-time tags to `TradeReview`, surfaces tags in review list/detail output, and supports exact tag filters on `list-trade-reviews`.

The slice stays narrow:

- tags are simple lowercase slugs
- tags are local review labels, not canonical taxonomy entities
- existing reviews are not edited in this slice
- no reporting/export surface is introduced yet
- no generated coaching or AI review content is introduced

## Second Implementation Slice

The second Milestone 5 slice is review quality scoring.

This slice adds optional 1-5 creation-time scores to `TradeReview` for:

- process quality
- setup quality
- execution quality
- exit quality

The scores are displayed in review list/detail output and can be filtered exactly through `list-trade-reviews`.

The slice stays narrow:

- existing reviews can remain unscored
- scores are review metadata, not analytics
- no review editing or backfill workflow is introduced
- no reporting/export surface is introduced yet
- no generated coaching or AI review content is introduced

## Third Implementation Slice

The third Milestone 5 slice is Markdown journal export for completed reviewed trades.

This slice adds `export-review-journal --output <path>` and reuses the existing review filters:

- rating
- purpose
- direction
- repeated tags
- process score
- setup quality
- execution quality
- exit quality
- sort order

The export writes one Markdown section per matching review and includes factual journal fields:

- review identity and reviewed timestamp
- linked position and trade plan identities
- purpose and direction
- realized P&L
- rating, tags, and quality scores
- summary, what went well, and what went poorly
- lessons learned and follow-up actions
- linked market-context metadata

The slice stays narrow:

- parent output directories must already exist
- existing files require explicit `--overwrite`
- empty results write no file
- context payloads stay isolated to `show-context`
- no CSV, charts, aggregate statistics, backup/restore, review editing, analytics, recommendations, or generated coaching are introduced

## Local Backup And Export Expectations

- the system should remain local-first
- backup and export workflows should be simple, explicit, and practical for a single-user setup
- exported data should preserve auditability and be suitable for local archiving
- operational guidance should favor straightforward restore and portability workflows over infrastructure-heavy solutions

## Acceptable Analytics Boundary

Analytics in this milestone should stay narrow and journal-grade.

Acceptable examples:

- filtering by review tags, instrument, direction, or timeframe
- simple counts or grouped summaries of completed reviewed trades
- export-ready review summaries for local analysis

Unacceptable expansion:

- portfolio engine behavior
- broad performance analytics sprawl
- optimization systems
- automated strategy evaluation

## Non-Goals

- portfolio management platform features
- broker-linked reporting pipelines
- cloud-first operational tooling
- AI-generated review content
- reinforcement learning or other ML-driven learning systems

## ADR Trigger

No ADR is needed for Milestone 5 unless the implementation introduces a durable reporting or export architecture rule that should govern future repository behavior.
