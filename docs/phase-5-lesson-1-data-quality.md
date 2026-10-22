# Phase 5 · Lesson 1 — Data Quality: A Green Pipeline Is Not a Correct Pipeline

> **Preview — Phase 5 · Lesson 1 of 1.** Read this to understand the idea. Do not build anything from this page yet; we implement it together in Phase 5, after the Phase 2 grain checkpoint.

---

## 1. What problem are we solving?

Imagine a Monday morning. `make load` printed its usual row counts. No errors.
The dashboard refreshed. Everything is green.

But the shop's export had a retry bug on Sunday night and wrote some order
lines **twice**. Every duplicated laptop line now counts its 1263.85 twice.
Revenue for Computers is up 8%. Marketing celebrates. Two weeks later finance
notices the warehouse revenue does not match the money that arrived in the bank.

Nothing crashed. Every step "succeeded". The data was simply wrong.

> A pipeline completing successfully does not mean the data is correct.

Code errors are loud: they stop the run. Data errors are quiet: they produce
plausible-looking numbers. Data tests are how we make them loud.

---

## 2. Plain-English explanation

A data test is a **question you ask the data after every load or build**,
written as a query that returns the rows that break a rule:

```text
"Show me every order line whose product does not exist."
   0 rows  → pass
   5 rows  → fail, and here are the 5 culprits
```

Each test encodes one thing we believe must always be true, **and why**. A test
without a business reason is noise; a business rule without a test is a hope.

---

## 3. Real-world analogy

A shop cashier works all day without a single error message from the till.
At closing time they still **count the cash drawer** and compare it with the
day's receipts. The till running smoothly says nothing about whether the
drawer matches.

Data tests are the end-of-day count for the warehouse. And, as a developer, you
already know the cousin: unit tests check that *code* behaves; data tests check
that the *data flowing through* behaves, on every run, because the data
changes every run even when the code does not.

---

## 4. E-commerce example: four basic tests and what they protect

| Test | Rule (example) | If it breaks, the business sees... |
| --- | --- | --- |
| **not_null** | `orders.customer_id` is never empty | Sales with no customer cannot be attributed to a region or segment. "Revenue by region" adds up to less than total revenue, and nobody can say where the gap went. |
| **unique** | `order_items.order_item_id` appears once | A duplicated line makes its revenue count twice. In a dimension, a duplicated `product_key` makes **every** sale of that product join twice. |
| **relationships** | every `fact_sales.customer_key` exists in `dim_customer.customer_key` | An orphan sale silently disappears from any report that joins to `dim_customer`. Total revenue and revenue by region disagree. |
| **accepted_values** | `orders.order_status` is one of pending / shipped / completed / cancelled | If the source starts sending `returned` or `Completed`, a filter like `order_status = 'completed'` silently drops or keeps the wrong orders. Revenue changes with no error. |

Notice that none of these failures crash anything. They all produce a number.
The number is just wrong.

---

## 5. Diagram: tests as gates between layers

```text
 CSV files ──► raw ──[tests]──► staging ──[tests]──► marts ──[tests]──► reports
                 │                 │                    │
                 ▼                 ▼                    ▼
          "did the source     "did our cleaning    "does the model obey
           send what we        keep every row       its grain and its
           expect?"            and value?"          relationships?"

  pass → continue        fail → stop (error) or flag (warning) and investigate
```

---

## 6. Official terminology

| Term | Plain meaning |
| --- | --- |
| **Data test** | A query that returns rows breaking a rule; zero rows means pass |
| **Generic test** | A reusable test you apply to a column by name: `not_null`, `unique`, `relationships`, `accepted_values` (built into dbt) |
| **Singular test** | A one-off SQL file for a specific business rule |
| **Referential integrity** | Every reference points at something that exists |
| **Orphan row** | A row whose reference points at nothing |
| **Reconciliation** | Comparing two numbers that must agree (e.g. header total vs sum of lines) |
| **Severity** | Whether a failure stops the pipeline (`error`) or just warns (`warn`) |

---

## 7. Small SQL examples (run today on `raw`)

Each query returns the **failing rows**. On freshly generated data every one
should return 0 rows. That is the point: a test is boring until the day it is
not.

**not_null** — order lines without a product:

```bash
make query SQL="SELECT count(*) AS failing_rows FROM raw.order_items WHERE product_id IS NULL"
```

**unique** — order lines that appear more than once:

```bash
make query SQL="SELECT order_item_id, count(*) AS copies FROM raw.order_items GROUP BY order_item_id HAVING count(*) > 1"
```

**relationships** — order lines pointing at a product that does not exist:

```bash
make query SQL="SELECT oi.order_item_id, oi.product_id FROM raw.order_items AS oi LEFT JOIN raw.products AS p ON p.product_id = oi.product_id WHERE p.product_id IS NULL"
```

**accepted_values** — order statuses outside the known list:

```bash
make query SQL="SELECT order_status, count(*) AS orders FROM raw.orders WHERE order_status NOT IN ('pending', 'shipped', 'completed', 'cancelled') GROUP BY order_status"
```

### Line by line: the relationships test

```sql
SELECT oi.order_item_id, oi.product_id
FROM raw.order_items AS oi
LEFT JOIN raw.products AS p ON p.product_id = oi.product_id
WHERE p.product_id IS NULL;
```

- `FROM raw.order_items AS oi` — start from the side that holds the reference
  (the "child").
- `LEFT JOIN raw.products AS p ON ...` — keep **every** order line, whether or
  not a matching product exists. When there is no match, all `p.` columns are
  `NULL`.
- `WHERE p.product_id IS NULL` — keep only the lines that found no product:
  the orphans.
- An `INNER JOIN` here would hide exactly the rows we are hunting for. That is
  also why orphans are dangerous in reports: most report queries use inner
  joins, so the orphan sales just vanish.

### A business-rule (singular) test: header vs lines

`orders.order_total` is supposed to equal the sum of its line net amounts.
That is a rule specific to our shop, so no built-in test covers it:

```bash
make query SQL="WITH line_totals AS (SELECT order_id, SUM(quantity * unit_price - discount_amount) AS sum_of_lines FROM raw.order_items GROUP BY order_id) SELECT o.order_id, o.order_total, l.sum_of_lines FROM raw.orders AS o JOIN line_totals AS l ON l.order_id = o.order_id WHERE o.order_total <> l.sum_of_lines"
```

Zero rows means the header copy and the lines agree. If they ever disagree,
you have to decide which one you trust, and that is a modelling decision, not
a test decision.

### Watching a duplicate inflate revenue (no tables needed)

This self-contained query fakes Alice's two order lines and a `dim_product`
that accidentally has the laptop **twice**:

```bash
make query SQL="WITH fact AS (SELECT * FROM (VALUES (3226, 11, 1263.85), (3226, 13, 50.00)) AS t(order_id, product_key, net_amount)), dim_product AS (SELECT * FROM (VALUES (11, 'Computers'), (11, 'Computers'), (13, 'Computers')) AS t(product_key, category)) SELECT d.category, SUM(f.net_amount) AS revenue FROM fact AS f JOIN dim_product AS d ON d.product_key = f.product_key GROUP BY d.category"
```

Alice's order is worth 1313.85, but the result says **2577.70**. Every query
ran without an error. A `unique` test on `dim_product.product_key` is what
catches this.

---

## 8. Future: the same tests declared in dbt (illustrative only)

In Phase 5 we will declare tests in YAML next to the dbt models, and
`dbt test` will generate and run queries like the ones above. The model and
column names below are **placeholders** that depend on your Phase 3 design,
and the exact YAML syntax will be checked against the installed dbt version
when we get there.

```yaml
# FUTURE (Phase 5): models/marts/marts.yml — does not exist yet
version: 2

models:
  - name: fact_sales
    columns:
      - name: order_item_id          # only if your grain is one row per order line
        data_tests:
          - not_null
          - unique
      - name: customer_key
        data_tests:
          - not_null
          - relationships:
              arguments:
                to: ref('dim_customer')
                field: customer_key
```

Every test line should be traceable to a sentence like "if this fails,
revenue by region is understated". If you cannot write that sentence, ask
whether the test is needed.

In Phase 5 we will also break data **on purpose** (in a controlled copy) so
you can watch each test fail and read its output. Do not edit `raw` or the
CSV files by hand now.

---

## 9. Common beginner mistakes

- **Thinking a successful run means correct data.** Exit code 0 means the SQL
  ran, nothing more.
- **Testing everything, or nothing.** A hundred tests without reasons get
  ignored; zero tests means you find problems in a meeting with finance.
- **Putting a `unique` test on the wrong grain.** `unique` only makes sense on
  the column(s) that identify one row. Know the grain first
  (what does one row represent?).
- **Using `INNER JOIN` to look for problems.** It hides orphans; use a
  `LEFT JOIN ... WHERE ... IS NULL`.
- **"Fixing" bad rows in raw by hand.** The next `make load` brings them back,
  and you lose the evidence. Fix the source, or handle it in staging, and
  write down why.
- **Silencing a failing test** instead of asking what changed in the business
  (a new status, a new payment method).
- **Only testing the final table.** Problems are cheaper to explain close to
  where they entered.

---

## 10. Small exercise

1. For each column below, decide whether it should be **unique** in its table.
   Write one sentence per answer about what one row represents.

   ```text
   raw.orders.order_id
   raw.order_items.order_id
   raw.payments.order_id
   raw.payments.payment_id
   raw.products.sku
   ```

2. Pick two columns that deserve an `accepted_values` test (other than
   `order_status`) and write, in one sentence each, the business consequence
   if a new value appeared.
3. Write (on paper first) the failing-rows query for "every payment points at
   an order that exists". Then run it with `make query`.
4. Your future `fact_sales` will exclude some orders on purpose (your status
   rule from Phase 3). Design a reconciliation check that proves no order line
   was lost *by accident*.

<details><summary>Hint</summary>

For 1, use the "one row = ..." sentences you wrote in Phase 2,
and remember that payments are events: attempts, successes and refunds.
For 3, copy the shape of the relationships query in section 7, swapping the
child and parent tables.
For 4, think in counts: lines in raw = lines in the fact + lines you excluded
deliberately. If the two sides differ, something vanished.

</details>

---

## 11. Before continuing, I should be able to explain:

```text
□ Why a successful pipeline run does not prove the data is correct
□ What a data test returns when it passes and when it fails
□ What not_null protects us from, with one business consequence
□ What unique protects us from, and how a duplicate doubles revenue
□ What relationships protects us from, and why orphans "vanish" in reports
□ What accepted_values protects us from, using order_status
□ The difference between a generic test and a singular (business-rule) test
□ Why every test needs a reason   ◄── Phase 5 goal: what each test protects us from
```

---

**Next →** [Phase 6 · Lesson 1 — Analytical SQL](phase-6-lesson-1-analytical-sql.md)
