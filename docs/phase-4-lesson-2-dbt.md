# Phase 4 · Lesson 2 — dbt: Transformations as Code

> **Preview — Phase 4 · Lesson 2 of 2.** Read this to understand the idea. Do not build anything from this page yet; we implement it together in Phase 4, after the Phase 2 grain checkpoint.

---

## 1. What problem are we solving?

In the previous lesson we saw that a transformation is just a
`SELECT` that reads one layer and produces the next. Soon we will have several:

```text
raw.orders       ─►  stg_orders       ─┐
raw.order_items  ─►  stg_order_items  ─┼─►  fact_sales  ─►  business queries
raw.products     ─►  stg_products     ─┼─►  dim_product
raw.customers    ─►  stg_customers    ─┴─►  dim_customer
```

If you manage these by hand, with a folder of `CREATE TABLE ... AS SELECT`
scripts, you quickly have to answer annoying questions:

- In which **order** must the scripts run? (`fact_sales` needs `stg_orders` first.)
- If I change `stg_orders`, **what else** must be rebuilt?
- How do I **test** each step and **document** what each column means?
- How do I run the same thing on my laptop and, later, on a cloud warehouse?

dbt is a tool that answers those questions for SQL transformations.

---

## 2. Plain-English explanation

A dbt project is a **folder of SELECT statements** plus a little configuration.
Each `.sql` file is one **model**: "this is how table/view X is built".

When you run dbt, it:

1. reads every model and finds which other models or sources it mentions,
2. works out the correct order,
3. wraps each SELECT in the right `CREATE VIEW ...` or `CREATE TABLE ...`,
4. sends that SQL to the warehouse (DuckDB for us), which does the actual work,
5. optionally runs data tests on the results.

That is all. dbt is not a database and does not store data. It writes and runs
SQL for you, in the right order.

### What dbt does NOT do

dbt **does not extract or load data**. It cannot pull rows out of the shop's
database or read our CSV files on its own. It only transforms data that is
**already in the warehouse**. In our project the E and L are done by
`scripts/load_data.py` (`make load`); dbt starts from the `raw` schema.

---

## 3. Real-world analogy

You already use one: **make**.

In our `Makefile`, each target lists what it depends on, and `make` runs things
in the right order. dbt is "make for SQL tables", with one difference: you do
not list dependencies by hand. dbt discovers them from the SQL itself, from
two special functions: `source()` and `ref()`.

```text
Makefile                          dbt
--------                          ---
target: dependency                model uses {{ ref('other_model') }}
recipe (shell commands)           a SELECT statement
make build                        dbt run
```

---

## 4. E-commerce example: the planned chain

The chain from the project brief is:

```text
stg_orders.sql   ──►   fact_sales.sql   ──►   business query
```

The snippets below are **illustrative only**. No dbt project exists in this
repository yet; we create it together in Phase 4, and your Phase 3 design
decisions will change `fact_sales`.

### Step 0: tell dbt where raw data lives (a "source")

```yaml
# FUTURE (Phase 4): models/staging/sources.yml — does not exist yet
version: 2

sources:
  - name: raw            # the name we use inside source('raw', ...)
    schema: raw          # the DuckDB schema created by make load
    tables:
      - name: orders
      - name: order_items
      - name: products
      - name: customers
```

### Step 1: a staging model reads from a source

```sql
-- FUTURE (Phase 4): models/staging/stg_orders.sql — does not exist yet
SELECT
    order_id,
    customer_id,
    order_status,
    ordered_at,
    updated_at
FROM {{ source('raw', 'orders') }}
```

### Step 2: a mart model reads from other models

```sql
-- FUTURE (Phase 4): models/marts/fact_sales.sql — does not exist yet
-- Placeholder only: the grain, keys, status rule and measures are YOUR
-- Phase 3 decisions and will replace what is written here.
SELECT
    oi.order_item_id,
    oi.order_id,
    o.customer_id,
    oi.product_id,
    o.ordered_at::DATE                                AS order_date,
    oi.quantity,
    oi.quantity * oi.unit_price - oi.discount_amount  AS net_amount
FROM {{ ref('stg_order_items') }} AS oi
JOIN {{ ref('stg_orders') }}      AS o ON o.order_id = oi.order_id
-- a status filter goes here once you decide which statuses count as a sale
```

### Step 3: a business query reads the mart

```sql
-- FUTURE: runs only after dbt has built fact_sales
SELECT
    date_trunc('month', order_date) AS month,
    SUM(net_amount)                 AS revenue
FROM fact_sales
GROUP BY month
ORDER BY month;
```

(Where exactly `fact_sales` lives, for example a `marts` schema, is decided in
Phase 4.)

---

## 5. Diagram: how dbt sees the project (the DAG)

```text
   source: raw.orders        source: raw.order_items
            │                          │
            ▼                          ▼
       stg_orders               stg_order_items
            │                          │
            └────────────┬─────────────┘
                         ▼
                    fact_sales
                         │
                         ▼
                 business queries / dashboards
```

dbt builds this graph by reading the `source()` and `ref()` calls. It never
needs to understand your joins. Because the arrows only go one way and never
loop, the graph is a **DAG** (directed acyclic graph). Viewed as "where did
this column come from?", the same graph is called **lineage**.

---

## 6. Official terminology

| Term | Plain meaning |
| --- | --- |
| **dbt project** | A folder with `dbt_project.yml` and your models |
| **profile** | Connection settings (`profiles.yml`): for us, the path to `warehouse/warehouse.duckdb` |
| **model** | One `.sql` file containing one SELECT; dbt turns it into a view or table of the same name |
| **source** | A table that dbt did not build (our raw tables), declared in YAML |
| **`source('raw', 'orders')`** | "the raw table `orders`"; dbt replaces it with the real table name |
| **`ref('stg_orders')`** | "the model `stg_orders`"; dbt replaces it with the real name **and** records the dependency |
| **DAG / lineage** | The graph of which model depends on which |
| **materialization** | How a model is saved: view, table, incremental, ephemeral |
| **Jinja** | The `{{ ... }}` templating language dbt uses inside SQL |
| **compile** | Turn Jinja-SQL into plain SQL, without running it |
| **data test** | A query that looks for bad rows (Phase 5) |
| **docs** | Descriptions in YAML plus a generated website with the lineage graph |

### Materializations at beginner level

| Materialization | dbt runs roughly... | Good for |
| --- | --- | --- |
| `view` (the default) | `CREATE VIEW stg_orders AS SELECT ...` | Light staging models; always fresh, no storage |
| `table` | `CREATE TABLE fact_sales AS SELECT ...` | Marts that many queries read; fast to query |
| `incremental` | Insert/merge only new rows | Big tables (Phase 8) |
| `ephemeral` | Nothing saved; inlined as a CTE into the models that use it | Small helper steps |

A common starting convention is "staging as views, marts as tables". We will
decide in Phase 4 whether it fits.

---

## 7. Line-by-line: what dbt does with `stg_orders.sql`

```sql
FROM {{ source('raw', 'orders') }}
```

- `{{ ... }}` — Jinja: "evaluate this before sending the SQL anywhere".
- `source('raw', 'orders')` — look up source `raw`, table `orders` in
  `sources.yml`. dbt replaces it with the fully qualified name, something like
  `"warehouse"."raw"."orders"`.

```sql
FROM {{ ref('stg_order_items') }} AS oi
JOIN {{ ref('stg_orders') }}      AS o ON o.order_id = oi.order_id
```

- `ref('stg_orders')` — "the model built from `stg_orders.sql`". dbt replaces
  it with the model's real location (its exact schema depends on configuration),
  **and** notes "`fact_sales` depends on `stg_orders`", so `stg_orders` is
  always built first.
- The rest is ordinary DuckDB SQL. dbt does not change it.

The final SQL dbt sends looks roughly like this (the schema name for the
view, here `staging`, depends on configuration we choose in Phase 4):

```sql
CREATE VIEW "warehouse"."staging"."stg_orders" AS
SELECT order_id, customer_id, order_status, ordered_at, updated_at
FROM "warehouse"."raw"."orders";
```

You will be able to read the exact compiled SQL in dbt's `target/` folder.
Nothing is hidden; it is SQL generation, not magic.

---

## 8. Commands

Runs **today** (dbt is installed in the Docker image, but there is no project):

```bash
make versions        # prints Python, DuckDB, dbt and pytest versions
```

**Future — added in Phase 4, does not exist yet:**

```text
dbt run      build every model in DAG order
dbt test     run the data tests
dbt build    run + test, model by model, in DAG order
dbt docs generate   build the documentation site with lineage
make dbt-run (future — added in Phase 4, does not exist yet)
```

### A note on versions

This project uses **dbt-core 1.12** with the **dbt-duckdb 1.11** adapter (see
`requirements.txt`). A newer generation, dbt v2 (the Rust-based "Fusion"
engine, installed with `pip install dbt`, with DuckDB support built in), has
been released but is still in Beta as of October 2026. We deliberately use the
stable 1.x line. The concepts on this page (models, `source()`, `ref()`, the
DAG, materializations, tests) are the same in both.

---

## 9. Common beginner mistakes

- **Thinking dbt extracts data from every source automatically.** It only
  transforms what is already in the warehouse. Our loader does the E and L.
- **Hard-coding table names** (`FROM staging.stg_orders`) instead of
  `{{ ref('stg_orders') }}`. The SQL may work, but dbt no longer knows the
  dependency and may build things in the wrong order.
- **Writing `CREATE TABLE` inside a model.** A model is only the SELECT; dbt
  adds the `CREATE`.
- **Thinking dbt is a database.** DuckDB stores and computes; dbt sends SQL.
- **One giant model.** If one file does renaming, cleaning, business rules
  and aggregation, you lose the benefits of layers.
- **Making everything a table "for speed"** before there is any speed problem.
- **Thinking `dbt run` succeeding means the numbers are right.** It means the
  SQL ran. Checking the numbers is Phase 5.

---

## 10. Small exercise

1. Using the future model list below, draw the DAG on paper:

   ```text
   stg_customers   reads source raw.customers
   stg_products    reads source raw.products
   stg_orders      reads source raw.orders
   stg_order_items reads source raw.order_items
   dim_customer    reads stg_customers
   dim_product     reads stg_products
   fact_sales      reads stg_orders, stg_order_items (and maybe dims?)
   ```

2. If `stg_products.sql` has a syntax error, which models can dbt still build,
   and which ones must it skip?
3. Someone writes `FROM raw.orders` inside `fact_sales.sql` instead of using
   `stg_orders`. What two things are lost?
4. For each model above, which materialization would you start with, and why?

<details><summary>Hint</summary>

For 2, follow the arrows downstream from `stg_products` only.
For 3, think about (a) the DAG and (b) the cleaning that staging is supposed
to do once for everybody. For `fact_sales`, ask yourself whether your design
puts surrogate keys on the fact table: if so, it must read the dimensions too.

</details>

---

## 11. Before continuing, I should be able to explain:

```text
□ What a dbt model is (one SELECT, one view/table)
□ Why dbt does not extract or load data, and what does that job in our project
□ The difference between source() and ref()
□ How dbt knows that fact_sales must be built after stg_orders
□ What a DAG / lineage graph is, using our planned models
□ The difference between view and table materializations
□ Why hard-coding table names breaks dependency tracking
□ Why a successful dbt run does not prove the data is correct
```

---

**Next →** [Phase 5 · Lesson 1 — Data quality](phase-5-lesson-1-data-quality.md)
