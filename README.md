# Data Warehouse Learning Project

Learn data warehousing from zero by building a small, real warehouse for a
fictional e-commerce shop — step by step, understanding *why* at every step.

```text
             PROJECT
                │
       ┌────────┴────────┐
       ▼                 ▼
    CODEBASE          COURSE (docs/)
 build warehouse     understand it
       └────────┬────────┘
                ▼
          LEARN BY DOING
```

The goal is not "a warehouse exists". The goal is that **you** can take a
question like *"What was monthly revenue by product category?"* and reason:

```text
Business question → What does one row represent? → Which fact? → Which dimensions?
→ Which measures? → Which joins? → Which aggregation? → SQL → Answer
```

---

# Start Here

**Open [Phase 1 · Lesson 1 — The big picture](docs/phase-1-lesson-1-big-picture.md)
and follow the "Next →" link at the bottom of each lesson.** That's it.

- Lessons are numbered in the order you read them: `phase-N-lesson-M-*.md`.
- Each lesson has everything you need on one page — commands included.
  You never have to come back to this README or open another file to
  continue.
- Setup (Docker, generating and loading the data) is a lesson too:
  Phase 1 · Lesson 2.

## The learning path

| Step | Lesson | You're done when you can… |
|---|---|---|
| **Phase 1 — Why warehouses exist** | | |
| 1 | [Phase 1 · Lesson 1 — The big picture](docs/phase-1-lesson-1-big-picture.md) | say in one sentence what a data warehouse is |
| 2 | [Phase 1 · Lesson 2 — Set up your warehouse](docs/phase-1-lesson-2-set-up-your-warehouse.md) | build, generate, load and query the warehouse |
| 3 | [Phase 1 · Lesson 3 — OLTP vs OLAP](docs/phase-1-lesson-3-oltp-vs-olap.md) | explain why a company uses a warehouse instead of querying its application database |
| **Phase 2 — Source data + grain** | | |
| 4 | [Phase 2 · Lesson 1 — Understanding the source data](docs/phase-2-lesson-1-understanding-source-data.md) | say what one row of each source table represents |
| 5 | [Phase 2 · Lesson 2 — Grain](docs/phase-2-lesson-2-grain.md) | explain exactly what one future row in `fact_sales` represents |
| 🛑 | **STOP — checkpoint.** Review your grain answers with the tutor before Phase 3. | |
| **Phase 3 — Facts and dimensions** *(preview)* | | |
| 6 | [Phase 3 · Lesson 1 — Facts and dimensions](docs/phase-3-lesson-1-facts-and-dimensions.md) | explain why each table exists and what one row represents |
| 7 | [Phase 3 · Lesson 2 — Star schema](docs/phase-3-lesson-2-star-schema.md) | draw the star for `fact_sales` |
| **Phase 4 — Raw / staging / marts, then dbt** *(preview)* | | |
| 8 | [Phase 4 · Lesson 1 — ETL vs ELT](docs/phase-4-lesson-1-etl-vs-elt.md) | explain why transformations are layered |
| 9 | [Phase 4 · Lesson 2 — dbt](docs/phase-4-lesson-2-dbt.md) | explain what dbt does for those layers |
| **Phase 5 — Data quality** *(preview)* | | |
| 10 | [Phase 5 · Lesson 1 — Data quality](docs/phase-5-lesson-1-data-quality.md) | explain what each test protects you from |
| **Phase 6 — Analytical SQL** *(preview)* | | |
| 11 | [Phase 6 · Lesson 1 — Analytical SQL](docs/phase-6-lesson-1-analytical-sql.md) | go from a business question to fact, dimensions, measures, joins, aggregation |
| **Phase 7 — Slowly changing dimensions** *(preview)* | | |
| 12 | [Phase 7 · Lesson 1 — Slowly changing dimensions](docs/phase-7-lesson-1-slowly-changing-dimensions.md) | explain replacing vs preserving history |
| **Phase 8 — Incremental loading** *(preview)* | | |
| 13 | [Phase 8 · Lesson 1 — Incremental loading](docs/phase-8-lesson-1-incremental-loading.md) | explain why incremental loads exist and why idempotency matters |
| **Phase 9 — Platform evolution** | discussion with the tutor, no lesson file | compare where this could go (PostgreSQL source, cloud warehouse, BI) |

**You are here:** Phase 2 (the milestone ends with the 🛑 checkpoint).
"Preview" lessons explain future ideas; nothing from them is built yet.
Don't jump to dbt — it only makes sense once grain, facts and dimensions do.

**Optional look-ups** (not part of the reading order — open only when you
need them): [glossary](docs/reference/glossary.md) ·
[Docker, just enough](docs/reference/docker.md) ·
[Claude Code setup](docs/reference/claude-skills.md)

---

## Commands

Explained step by step in Phase 1 · Lesson 2; this is the quick reference.
Everything runs in Docker — you only need Git and Docker on your computer.

| Command | What it does |
|---|---|
| `make help` | List the commands |
| `make build` | Build the Docker image (Python 3.13, DuckDB, dbt, pytest) |
| `make generate-data` | Generate the synthetic source CSVs (same data every time, seed 42) |
| `make load` | Full-refresh the CSVs into `warehouse/warehouse.duckdb`, schema `raw` — **disconnect TablePlus first** |
| `make query SQL="..."` | Run one SQL query, read-only, e.g. `make query SQL="SELECT count(*) FROM raw.orders"` |
| `make test` | Run the Python tests |
| `make shell` | Open a shell inside the container |
| `make versions` | Show tool versions inside the container |
| `make down` | Remove leftover containers (keeps your data and warehouse) |
| `make clean` | **Delete** the generated CSVs and the warehouse file |

dbt is installed in the image, but there is no dbt project yet — dbt
commands arrive in Phase 4.

---

## How it fits together

```text
scripts/generate_data.py           scripts/load_data.py
  (seed 42, deterministic)           (full refresh, one transaction)
          │                                   │
          ▼                                   ▼
  data/source/*.csv  ──────────────►  warehouse/warehouse.duckdb
  "the shop's database export"          schema raw: customers, products,
                                        orders, order_items, payments
                                                   │
                                                   ▼
                                       TablePlus / make query
```

```text
.
├── Dockerfile, compose.yaml, Makefile   the dev environment
├── requirements.txt                     pinned Python packages
├── pyproject.toml                       pytest configuration
├── scripts/
│   ├── source_schema.py                 the source tables and column types
│   ├── generate_data.py                 synthetic source data
│   ├── load_data.py                     CSV → DuckDB raw schema
│   └── query.py                         read-only query helper
├── tests/                               pytest: our assumptions about the data
├── data/source/                         generated CSVs (git-ignored)
├── warehouse/                           warehouse.duckdb (git-ignored)
├── docs/                                the course: phase-N-lesson-M-*.md, in reading order
│   └── reference/                       glossary, Docker guide, Claude Code setup
├── CLAUDE.md                            guidance for Claude Code
└── .claude/                             Claude Code settings + project agents
```

## Learning with Claude Code

Start a tutoring session:

```bash
claude --agent data-warehouse-tutor
```

The tutor explains, asks you questions, and reviews your answers — it
won't do the important thinking for you. See
[docs/reference/claude-skills.md](docs/reference/claude-skills.md) for the full setup
(Superpowers + project agents).
