# Phase 4 · Lesson 1 — ETL vs ELT: Where Does the Reshaping Happen?

> **Preview — Phase 4 · Lesson 1 of 2.** Read this to understand the idea. Do not build anything from this page yet; we implement it together in Phase 4, after the Phase 2 grain checkpoint.

---

## 1. What problem are we solving?

Our shop's data starts in the application database (for us: the CSV files in
`data/source/`). The answers we want (monthly revenue by category, revenue by
region) need data that is reshaped: line amounts computed, statuses decided,
descriptions attached.

Somebody has to do that reshaping. The real question is not the acronym, it
is:

> **Where** does the reshaping happen, and **what do we keep** from before it
> happened?

That choice decides how easily you can fix a mistake, re-answer an old
question differently, or explain where a number came from.

---

## 2. Plain-English explanation

There are three jobs:

```text
Extract    copy data out of the source system
Load       put it into the warehouse
Transform  clean it, reshape it, apply business rules
```

**ETL** does the transform *in between*: data is cleaned on its way to the
warehouse, and only the cleaned result is stored.

**ELT** loads the data first, **as-is**, and transforms it *inside* the
warehouse, with SQL, as many times as needed.

Same three jobs. Different order. Different consequences.

---

## 3. Real-world analogy

Think about getting dinner from a farm.

- **ETL** is a meal-kit service. The farm washes, chops and cooks before
  delivering. You receive finished dishes. If you wanted the carrots diced
  instead of sliced, too bad: the whole carrots are gone.
- **ELT** is a grocery delivery. Raw ingredients go into your fridge. You
  cook in your own kitchen. If a recipe goes wrong, the ingredients are still
  in the fridge and you can cook it again a different way.

The fridge is the **raw layer**. The kitchen is the **warehouse engine**
(DuckDB). The recipes are SQL **transformations**.

---

## 4. E-commerce example: what our project already does

Look at what `make load` does today (`scripts/load_data.py`):

```text
data/source/orders.csv  ──►  warehouse/warehouse.duckdb : raw.orders
```

- It does **not** rename columns, filter rows, fix values or join tables.
- It only adds two bookkeeping columns: `_source_file` and `_loaded_at`.
- Every run is a full refresh: tables are replaced, never appended to, so
  running it twice does not duplicate rows.

So today we have done **E** and **L**. Nothing is transformed yet. That makes
our project ELT-shaped: the **T** will happen later, inside DuckDB, in the
staging and marts layers.

You can see the untouched raw data and its bookkeeping columns now:

```bash
make query SQL="SELECT order_id, order_status, order_total, _source_file, _loaded_at FROM raw.orders ORDER BY order_id LIMIT 3"
```

---

## 5. Diagram

```text
ETL
                 ┌──────────────────┐
  source  ──E──► │ transform engine │ ──L──►  warehouse
  (shop DB)      │ (outside the DW) │        (clean tables only)
                 └──────────────────┘

ELT  (our project)
                                ┌─────────────── warehouse (DuckDB) ───────────────┐
  source  ──E──►  CSV  ──L──►   │  raw  ──T──►  staging  ──T──►  marts             │
  (shop DB)       files         │  as-is        renamed,         facts,            │
                                │               typed,           dimensions        │
                                │               cleaned          (Phase 3/4)       │
                                └──────────────────────────────────────────────────┘
  generate_data.py              load_data.py       (future: dbt, next lesson)
  (pretend extract)             EXISTS TODAY       DOES NOT EXIST YET
```

---

## 6. Official terminology

| Term | Plain meaning | In our project |
| --- | --- | --- |
| **Extract** | Read data out of a source system | `generate_data.py` pretends to be an export |
| **Load** | Write it into the warehouse | `load_data.py` → schema `raw` |
| **Transform** | Clean, reshape, apply business rules | future staging and marts |
| **Raw layer** | Source data preserved with minimal change | `raw.orders`, `raw.order_items`, ... |
| **Staging layer** | Light cleanup: rename, cast types, standardise | future `stg_*` models |
| **Marts layer** | Business-ready facts and dimensions | future `fact_sales`, `dim_*` |
| **Full refresh** | Rebuild a table completely on every run | how `make load` works |

The layer idea in one picture:

```text
RAW       keep what the source gave us           "the fridge"
STAGING   rename, cast, standardise, basic clean "washing and chopping"
MARTS     facts, dimensions, business rules      "the cooked meal"
```

---

## 7. Architectural consequences (the part that matters)

| Question | ETL | ELT |
| --- | --- | --- |
| Can I re-run a transformation after fixing a bug? | Only by extracting again from the source | Yes, raw is still there |
| Can I answer a new question that needs a column we dropped? | No, it was never stored | Yes, if it is in raw |
| Where does the compute happen? | A separate transformation server/tool | The warehouse engine itself |
| What language are transformations written in? | Often a tool's own language or code | Mostly SQL |
| Can I trace a number back to the source row? | Harder | Raw is the audit trail |
| Storage cost | Lower, only results are kept | Higher, raw is kept too |
| Sensitive data (e.g. emails) | Can be removed **before** it lands | Lands in raw; must be protected there |

ELT became popular because modern analytical engines (BigQuery, Snowflake,
DuckDB on a laptop) are fast and storage is cheap. Keeping raw data and
transforming with SQL inside the engine is usually simpler than running a
separate transformation server. ETL is not wrong or obsolete; it still makes
sense when data must be filtered or anonymised before it is allowed to land.

---

## 8. Small SQL example: a transformation is just a SELECT

A transformation in ELT is a query that reads one layer and produces the next.
This one runs on today's raw data and shows the kind of thing a staging step
might compute:

```sql
SELECT
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount_amount,
    quantity * unit_price                   AS gross_amount,
    quantity * unit_price - discount_amount AS net_amount
FROM raw.order_items
WHERE order_id = 3226;
```

Try it:

```bash
make query SQL="SELECT order_item_id, order_id, product_id, quantity, unit_price, discount_amount, quantity * unit_price AS gross_amount, quantity * unit_price - discount_amount AS net_amount FROM raw.order_items WHERE order_id = 3226"
```

Line by line:

- `FROM raw.order_items` — the input is the untouched raw table. We never
  modify it; we only read from it.
- The first six columns are passed through unchanged.
- `quantity * unit_price AS gross_amount` — a derived value: the price before
  discount.
- `quantity * unit_price - discount_amount AS net_amount` — the money the line
  actually brought in (the discount is for the whole line).
- `WHERE order_id = 3226` — only to keep the output small; Alice's order.

`make query` opens the warehouse **read-only**, so it can only show results.
Saving a result as a new table or view is the job of the future
transformation step. It would look roughly like this:

```sql
-- FUTURE (Phase 4), illustrative only: schema `staging` does not exist yet,
-- and in this project dbt will create it for us (next lesson).
CREATE OR REPLACE VIEW staging.stg_order_items AS
SELECT
    order_item_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    discount_amount
FROM raw.order_items;
```

Whether `net_amount` is computed in staging or in the mart is one of your
Phase 4 design decisions.

---

## 9. Why layers instead of one huge query?

You *could* answer "monthly revenue by category" with one 60-line query
straight from `raw`. Layers exist because:

- **Reuse.** The net-amount formula and the status rule are written once and
  used by every report, instead of copy-pasted.
- **Debugging.** If revenue looks wrong, you can check raw, then staging, then
  the fact, and find the step where it went wrong.
- **Testing.** Each layer can be tested on its own (Phase 5).
- **Change.** If the source renames a column, only the staging model changes.

But: do not create layers just to look sophisticated. Our plan is
`raw → staging → marts`. An extra "intermediate" layer is added only if a real
transformation needs it.

---

## 10. Common beginner mistakes

- **Treating ETL vs ELT as vocabulary.** The useful question is "where does the
  logic live, and can I rebuild from what I kept?"
- **Transforming inside raw.** If raw is "fixed up", you lose the record of what
  the source actually sent. Raw stays as-is.
- **Editing raw tables by hand** to make a report look right. The next
  `make load` wipes the fix, and nobody knows it happened.
- **Thinking ELT means no cleaning.** ELT moves cleaning later, it does not
  remove it.
- **Thinking ELT is always better.** Privacy or volume constraints can make
  "transform before load" the right call.
- **Putting business rules in staging.** "Which statuses count as a sale" is a
  business decision; staging is for renaming, casting and standardising.

---

## 11. Small exercise

For each transformation, decide which layer it belongs in (raw, staging or
marts) and write one sentence explaining why:

```text
a) Rename order_status to status
b) Cast processed_at from text to TIMESTAMP (if it had arrived as text)
c) Compute net_amount per order line
d) Exclude cancelled orders from revenue
e) Attach category and brand to each sale
f) Add _loaded_at to each row
g) Trim spaces and lower-case email addresses
```

Then: imagine a bug in your future `fact_sales` that used `list_price` instead
of `unit_price` for six months. With our ELT setup, what would you need to do
to fix the history? What would you need under ETL?

<details><summary>Hint</summary>

Ask of each step: is it about *how the source spells things* (staging), *what
the business means* (marts), or *bookkeeping about the load itself*? For the
bug question, think about which layer still holds the price that was actually
paid.

</details>

---

## 12. Before continuing, I should be able to explain:

```text
□ What extract, load and transform each mean in our project
□ Why our project is ELT-shaped, pointing at make load and the raw schema
□ What "raw" promises, and why we never edit it
□ What staging does versus what marts do
□ Two consequences of ELT (re-running, auditability, storage, privacy...)
□ One situation where ETL is the better choice
□ Why layered transformations beat one huge SQL query   ◄── Phase 4 goal
```

---

**Next →** [Phase 4 · Lesson 2 — dbt](phase-4-lesson-2-dbt.md)
