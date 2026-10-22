# Glossary

Every term in this project, in plain English, with an example from our
own shop. Tables marked **(future)** do not exist yet — today the
warehouse contains only the `raw` schema (`raw.customers`,
`raw.products`, `raw.orders`, `raw.order_items`, `raw.payments`).

Jump to: [The big picture](#the-big-picture) ·
[Two kinds of work](#two-kinds-of-work) ·
[Moving data](#moving-data) ·
[Modeling](#modeling) ·
[Keys](#keys) ·
[Schema shapes](#schema-shapes) ·
[Change over time](#change-over-time) ·
[Loading](#loading) ·
[Tools and trust](#tools-and-trust)

---

## The big picture

### Data warehouse

**Plain English:** A database built for *answering questions* about the business: history from many systems, cleaned up and organized for analysis rather than for running the shop.

**Project example:** `warehouse/warehouse.duckdb`. Today it holds only the `raw` schema; staging and marts come later.

**Learn more:** [Phase 1 · Lesson 1 — The big picture](../phase-1-lesson-1-big-picture.md)

### Database

**Plain English:** An organized store of data you can query and change, usually with SQL. A warehouse is one kind of database; the shop's application database is another kind.

**Project example:** The DuckDB file `warehouse/warehouse.duckdb` is a database. So is the shop's (fictional) application database that our CSVs pretend to be exported from.

**Learn more:** [Phase 1 · Lesson 3 — OLTP vs OLAP](../phase-1-lesson-3-oltp-vs-olap.md)

### Data lake

**Plain English:** Cheap storage for files of any shape (CSV, JSON, logs, images), kept as-is until someone needs them. Flexible, but no tidy tables by default.

**Project example:** The closest thing we have is `data/source/*.csv` — plain files waiting to be loaded. We do not build a real data lake.

**Learn more:** [Phase 1 · Lesson 1 — The big picture](../phase-1-lesson-1-big-picture.md)

### Data mart

**Plain English:** A slice of the warehouse prepared for one topic or team, such as "sales", so they can answer their questions without understanding everything else.

**Project example:** The marts layer **(future)**: `fact_sales` with `dim_customer`, `dim_product` and `dim_date`.

**Learn more:** [Phase 1 · Lesson 1 — The big picture](../phase-1-lesson-1-big-picture.md)

### Schema

**Plain English:** Two meanings. (1) A named folder of tables inside a database. (2) The shape of a table: its columns and their types.

**Project example:** (1) `raw` is a schema, so we write `raw.orders`. (2) `scripts/source_schema.py` defines the columns and types of every source table.

**Learn more:** [Phase 2 · Lesson 1 — Understanding the source data](../phase-2-lesson-1-understanding-source-data.md)

---

## Two kinds of work

### OLTP

**Plain English:** "Online Transaction Processing" — systems that *run* the business: many tiny, fast reads and writes, one customer at a time.

**Project example:** The shop's website database that records Alice's checkout (simulated by our generated CSVs).

**Learn more:** [Phase 1 · Lesson 3 — OLTP vs OLAP](../phase-1-lesson-3-oltp-vs-olap.md)

### OLAP

**Plain English:** "Online Analytical Processing" — systems that *understand* the business: few, big queries that read many rows to summarize them.

**Project example:** DuckDB scanning every row of `raw.order_items` to compute monthly revenue.

**Learn more:** [Phase 1 · Lesson 3 — OLTP vs OLAP](../phase-1-lesson-3-oltp-vs-olap.md)

### Source system

**Plain English:** Where the data is born. The warehouse copies from it and never writes back to it.

**Project example:** The fictional shop application. `scripts/generate_data.py` plays its role by writing `data/source/*.csv`.

**Learn more:** [Phase 2 · Lesson 1 — Understanding the source data](../phase-2-lesson-1-understanding-source-data.md)

---

## Moving data

### ETL

**Plain English:** Extract, Transform, Load — clean and reshape the data *before* it enters the warehouse, usually in a separate tool.

**Project example:** Not what we do. If `scripts/load_data.py` filtered out cancelled orders before writing them, that would be ETL-style.

**Learn more:** [Phase 4 · Lesson 1 — ETL vs ELT](../phase-4-lesson-1-etl-vs-elt.md)

### ELT

**Plain English:** Extract, Load, *then* Transform — copy the data in unchanged first, then reshape it with SQL inside the warehouse.

**Project example:** Our approach. `make load` copies the CSVs unchanged into `raw`; staging and marts will be built from `raw` with SQL **(future)**.

**Learn more:** [Phase 4 · Lesson 1 — ETL vs ELT](../phase-4-lesson-1-etl-vs-elt.md)

### Raw data

**Plain English:** Data exactly as the source gave it — no renaming, no fixing, no filtering. Your safety copy of the truth.

**Project example:** `raw.orders`, `raw.order_items`, etc.: the CSV columns plus two bookkeeping columns, `_source_file` and `_loaded_at`.

**Learn more:** [Phase 2 · Lesson 1 — Understanding the source data](../phase-2-lesson-1-understanding-source-data.md)

### Staging

**Plain English:** The first cleanup layer: rename, cast types, standardize values, one model per source table. No business logic yet.

**Project example:** **(future)** e.g. `stg_orders`, built from `raw.orders`.

**Learn more:** [Phase 4 · Lesson 1 — ETL vs ELT](../phase-4-lesson-1-etl-vs-elt.md)

### Lineage

**Plain English:** The family tree of a number: which tables and steps produced it, so you can trace a wrong figure back to its origin.

**Project example:** Today: `data/source/orders.csv` → `raw.orders` (recorded in `_source_file`). Later: `raw.order_items` → `stg_order_items` → `fact_sales` **(future)**.

**Learn more:** [Phase 4 · Lesson 2 — dbt](../phase-4-lesson-2-dbt.md)

---

## Modeling

### Grain

**Plain English:** What exactly one row represents. Decide it first; almost every later mistake traces back to an unclear grain.

**Project example:** One row in `raw.order_items` = one product line in one order. The planned `fact_sales` **(future)** uses the same grain.

**Learn more:** [Phase 2 · Lesson 2 — Grain](../phase-2-lesson-2-grain.md)

### Fact

**Plain English:** A row that records something that *happened*, with numbers attached that you can add up.

**Project example:** **(future)** A `fact_sales` row: order 3226, Laptop 14-inch, quantity 1, net amount 1263.85.

**Learn more:** [Phase 3 · Lesson 1 — Facts and dimensions](../phase-3-lesson-1-facts-and-dimensions.md)

### Dimension

**Plain English:** The descriptive context you slice facts by — who, what, when, where.

**Project example:** **(future)** `dim_customer` (city, region, customer_segment), `dim_product` (category, brand), `dim_date` (month, year).

**Learn more:** [Phase 3 · Lesson 1 — Facts and dimensions](../phase-3-lesson-1-facts-and-dimensions.md)

### Measure

**Plain English:** A number stored on a fact row that you aggregate (sum, count, average).

**Project example:** `quantity`, `unit_price` and `discount_amount` in `raw.order_items`; the line's net amount = `quantity * unit_price - discount_amount`.

**Learn more:** [Phase 3 · Lesson 1 — Facts and dimensions](../phase-3-lesson-1-facts-and-dimensions.md)

### Additive measure

**Plain English:** A measure you can safely sum across any dimension. Averages, ratios and distinct counts are *not* additive.

**Project example:** Quantity and net amount are additive. Average order value and "number of distinct customers" are not — summing monthly values gives nonsense.

**Learn more:** [Phase 6 · Lesson 1 — Analytical SQL](../phase-6-lesson-1-analytical-sql.md)

### Metric

**Plain English:** A business-defined calculation built from measures, including rules about what counts.

**Project example:** Average order value = total revenue / number of orders, counting only `completed` orders (a business decision).

**Learn more:** [Phase 6 · Lesson 1 — Analytical SQL](../phase-6-lesson-1-analytical-sql.md)

### Fan-out

**Plain English:** A join that multiplies rows, so numbers from the "one" side get counted several times.

**Project example:** Joining `raw.orders` to `raw.order_items` repeats `order_total` once per line; summing it afterwards inflates revenue (about 2.4 times in our data).

**Learn more:** [Phase 6 · Lesson 1 — Analytical SQL](../phase-6-lesson-1-analytical-sql.md)

---

## Keys

### Primary key

**Plain English:** The column (or columns) that uniquely identifies each row in a table.

**Project example:** `order_id` in `raw.orders`, `order_item_id` in `raw.order_items`. The raw tables do not enforce this; checking it is a data-quality test.

**Learn more:** [Phase 3 · Lesson 1 — Facts and dimensions](../phase-3-lesson-1-facts-and-dimensions.md)

### Foreign key

**Plain English:** A column that points at the primary key of another table — "this row belongs to that row".

**Project example:** `raw.order_items.order_id` → `raw.orders.order_id`; `raw.orders.customer_id` → `raw.customers.customer_id`.

**Learn more:** [Phase 3 · Lesson 1 — Facts and dimensions](../phase-3-lesson-1-facts-and-dimensions.md)

### Natural key

**Plain English:** An id that comes from the source system or the real world, with meaning outside the warehouse.

**Project example:** `customer_id`, `product_id`, `sku`. Alice is `customer_id = 1` in the app and in the warehouse.

**Learn more:** [Phase 3 · Lesson 1 — Facts and dimensions](../phase-3-lesson-1-facts-and-dimensions.md)

### Surrogate key

**Plain English:** An id the warehouse invents for its own rows. It has no meaning outside the warehouse.

**Project example:** **(future)** `customer_key` in `dim_customer`. With SCD Type 2, Alice has one `customer_id` but one `customer_key` per version.

**Learn more:** [Phase 3 · Lesson 1 — Facts and dimensions](../phase-3-lesson-1-facts-and-dimensions.md), [Phase 7 · Lesson 1 — Slowly changing dimensions](../phase-7-lesson-1-slowly-changing-dimensions.md)

---

## Schema shapes

### Star schema

**Plain English:** One fact table in the middle, joined directly to flat dimension tables around it. Drawn out, it looks like a star.

**Project example:** **(future)** `fact_sales` surrounded by `dim_customer`, `dim_product` and `dim_date`.

**Learn more:** [Phase 3 · Lesson 2 — Star schema](../phase-3-lesson-2-star-schema.md)

### Snowflake schema

**Plain English:** A star schema whose dimensions are split into further sub-tables. Less repetition, more joins.

**Project example:** **(future, not planned)** Moving `category` out of `dim_product` into its own `dim_category` table.

**Learn more:** [Phase 3 · Lesson 2 — Star schema](../phase-3-lesson-2-star-schema.md)

---

## Change over time

### SCD

**Plain English:** "Slowly Changing Dimension" — the rule for what happens when a descriptive detail (city, segment, category) changes.

**Project example:** Alice moves from Ho Chi Minh City to Da Nang in June 2026. Where should her January sale be reported?

**Learn more:** [Phase 7 · Lesson 1 — Slowly changing dimensions](../phase-7-lesson-1-slowly-changing-dimensions.md)

### SCD Type 1

**Plain English:** Overwrite the old value. Simple, but history is rewritten: the past looks as if the new value was always true.

**Project example:** `raw.customers` already behaves like this: it keeps only the current `city`. If Alice moved to Da Nang, her January sale would then show up under Da Nang.

**Learn more:** [Phase 7 · Lesson 1 — Slowly changing dimensions](../phase-7-lesson-1-slowly-changing-dimensions.md)

### SCD Type 2

**Plain English:** Keep every version as its own row, with the time window it was valid. History stays true.

**Project example:** **(future)** `dim_customer` with `customer_key`, `customer_id`, `city`, `valid_from`, `valid_to`, `is_current`.

**Learn more:** [Phase 7 · Lesson 1 — Slowly changing dimensions](../phase-7-lesson-1-slowly-changing-dimensions.md)

---

## Loading

### Full refresh

**Plain English:** Throw the table away and rebuild it from all the source data, every time. Slow on huge data, but hard to get wrong.

**Project example:** `make load` — `CREATE OR REPLACE TABLE` for every raw table, inside one transaction.

**Learn more:** [Phase 8 · Lesson 1 — Incremental loading](../phase-8-lesson-1-incremental-loading.md)

### Incremental load

**Plain English:** Process only the rows that are new or changed since the last run, and merge them in.

**Project example:** **(future)** Load only orders whose `updated_at` is newer than last time, and update orders that went from `shipped` to `completed`.

**Learn more:** [Phase 8 · Lesson 1 — Incremental loading](../phase-8-lesson-1-incremental-loading.md)

### Watermark

**Plain English:** The bookmark that says "I have processed everything up to here", usually the latest `updated_at` already loaded.

**Project example:** **(future)** `max(updated_at)` of `raw.orders` after the last successful load.

**Learn more:** [Phase 8 · Lesson 1 — Incremental loading](../phase-8-lesson-1-incremental-loading.md)

### Idempotency

**Plain English:** Running the same pipeline twice with the same input gives the same result as running it once — no duplicates, no corruption.

**Project example:** Running `make load` twice still gives the same row counts in `raw.orders` (checked by `make test`).

**Learn more:** [Phase 8 · Lesson 1 — Incremental loading](../phase-8-lesson-1-incremental-loading.md)

---

## Tools and trust

### dbt

**Plain English:** A tool that runs your SQL `SELECT` files inside the warehouse in the right order, and adds tests and documentation. It does **not** extract data from source systems.

**Project example:** dbt-core 1.12 and dbt-duckdb 1.11 are installed in the container (`make versions`), but there is no dbt project yet **(future)**.

**Learn more:** [Phase 4 · Lesson 2 — dbt](../phase-4-lesson-2-dbt.md)

### dbt model

**Plain English:** One `.sql` file containing one `SELECT`. dbt turns it into a table or view named after the file.

**Project example:** **(future)** A `stg_orders.sql` file that selects from `raw.orders`.

**Learn more:** [Phase 4 · Lesson 2 — dbt](../phase-4-lesson-2-dbt.md)

### Materialization

**Plain English:** How dbt saves a model's result: as a view, a table, or incrementally.

**Project example:** **(future)** We will choose a materialization for each layer when we build the dbt project.

**Learn more:** [Phase 4 · Lesson 2 — dbt](../phase-4-lesson-2-dbt.md)

### Data quality

**Plain English:** Whether the data is correct, complete and consistent enough to trust. A pipeline that "ran successfully" can still produce wrong data.

**Project example:** Checks such as "`order_id` is unique in `raw.orders`" and "`order_total` equals the sum of the order's line net amounts".

**Learn more:** [Phase 5 · Lesson 1 — Data quality](../phase-5-lesson-1-data-quality.md)
