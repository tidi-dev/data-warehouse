# CLAUDE.md — Data Warehouse Learning Project

This repository is a **course + codebase**: a software developer learns data
warehousing by building a small DuckDB + dbt warehouse for a fictional
e-commerce shop. `prompt.txt` is the original brief and the source of truth
for scope. Learning material in `docs/` is a first-class deliverable.

## Current phase and STOP point

- **Implemented:** Phase 1–2 infrastructure — Docker dev environment,
  deterministic source data generator, full-refresh loader into DuckDB schema
  `raw`, pytest suite, lessons for phases 1–8, glossary, docker guide.
- **Learner is at:** Phase 2 checkpoint (`docs/phase-2-lesson-2-grain.md`,
  section 9: propose the `fact_sales` grain).
- **STOP:** do NOT implement facts, dimensions, a dbt project, staging/mart
  models, SCD2 or incremental loading until the learner has answered the
  Phase 2 checkpoint and explicitly asks to start Phase 3.

The learner updates this section as phases are completed.

## Educational safety rule (overrides any workflow skill)

For learning-critical decisions — choosing grain, designing fact_sales,
choosing dimensions, deciding measures, writing important joins, designing
SCD2, designing incremental loads — **teach → ask → let the learner attempt
→ review → correct**. Don't generate the complete solution unless the
learner explicitly asks after attempting. Never race through phases.

When a Superpowers skill (e.g. brainstorming, writing-plans) would have
Claude make one of these decisions, the learner makes it instead; Claude
facilitates and reviews. Pure tutoring conversations do not need the
brainstorming/planning workflow.

## Course layout

- Lessons: `docs/phase-N-lesson-M-<topic>.md`, named in reading order; the
  README's "learning path" table is the only index.
- Each lesson is self-contained and read straight through: it ends with a
  single `**Next →**` link, never asks the learner to go back to the README
  or another lesson, and mentions other lessons as plain text, not links.
  Commands needed in a lesson are written in that lesson.
- Optional look-ups (glossary, Docker guide, Claude Code setup) live in
  `docs/reference/` and are never required reading.

## Commands (everything runs in Docker — never require host Python/dbt)

```text
make build           build the dev image
make generate-data   write data/source/*.csv (seed 42, deterministic)
make load            full-refresh CSVs into warehouse/warehouse.duckdb, schema raw  (WRITES)
make query SQL="..." run SQL read-only
make test            pytest
make shell           bash in the container
make versions        tool versions
make down            remove containers (keeps data and warehouse)
make clean           DELETE generated CSVs and warehouse file
```

Only document commands that exist. dbt commands get Makefile targets in
Phase 4, when a dbt project exists.

## Architecture constraints

- One dev container (`compose.yaml`, service `dev`); project bind-mounted at
  `/workspace`. No database server container, no exposed ports — DuckDB is
  embedded and lives in `warehouse/warehouse.duckdb` on the host.
- One writer at a time. File locks do **not** cross the macOS host ↔
  container boundary (verified), so the learner must disconnect TablePlus
  before writing commands.
- Dependencies pinned in `requirements.txt` (duckdb 1.5.6, dbt-core 1.12.5,
  dbt-duckdb 1.11.0, pytest 9.1.1) on `python:3.13-slim`. dbt v2 (Fusion)
  is deliberately not used yet (Beta as of 2026-10).
- Source schema contract: `scripts/source_schema.py` (used by generator,
  loader and tests). Money is `DECIMAL(10,2)`.
- Out of scope until much later: cloud warehouses, orchestrators, Kafka/Spark,
  Kubernetes, Terraform, BI platforms.

## Data facts worth knowing (seed 42)

- Orders 2025-01-01 … 2026-09-30; export taken 2026-10-01 00:00.
- Alice = customer_id 1 (Ho Chi Minh City); her example order is 3226
  (Laptop 14-inch ×1 @ 1263.85, Wireless Mouse ×2 @ 25.00).
- `products.list_price` is today's price (≈⅓ of products rose on
  2026-01-01); `order_items.unit_price` is the price paid.
- `payments` = one row per payment event (failed / succeeded / refunded);
  orders have 0–3 payment rows. `orders.order_total` is a header-level copy
  of the line amounts → fan-out trap.

## Tests

Test our assumptions and our code, not DuckDB/dbt internals. No tests just
to raise the count.

## Claude Code setup

See `docs/reference/claude-skills.md`. Superpowers (project scope) with a reduced
skill set (others denied in `.claude/settings.json`); project agents in
`.claude/agents/`: `data-warehouse-tutor`, `data-modeling-reviewer`,
`data-quality-reviewer`.
