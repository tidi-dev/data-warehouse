# Phase 3 · Lesson 2 — Star Schema: One Fact in the Middle, Descriptions Around It

> **Preview — Phase 3 · Lesson 2 of 2.** Read this to understand the idea. Do not build anything from this page yet; we implement it together in Phase 3, after the Phase 2 grain checkpoint.

---

## 1. What problem are we solving?

Take one question: *"What was monthly revenue by product category?"*

Against the raw tables you must remember that:

- revenue comes from `order_items` (quantity × unit_price − discount),
- the month comes from `orders.ordered_at`, one join away,
- the category comes from `products`, another join away,
- you must not touch `orders.order_total` or `payments`, or you double-count,
- you must decide which order statuses count.

Every analyst, every dashboard, every week, re-solves the same puzzle. Some of
them will get it wrong. The source schema is shaped for **writing** orders
quickly and safely (the OLTP side, from Phase 1), not for
**reading** history.

A star schema is a shape built for the reading side: every question becomes
"start at the fact table, join one hop to the descriptions you need, group,
sum".

---

## 2. Plain-English explanation

Put the table of events (the fact table: one row per thing that happened,
with the numbers you add up) in the middle.
Put each kind of description (customer, product, date) in its own table
around it. Each description table is joined **directly** to the fact table,
never through another description table.

Drawn on paper it looks like a star: one centre, several points.

---

## 3. Real-world analogy

Think of a bicycle wheel. The hub is the fact table. Each spoke goes straight
from the hub to the rim; no spoke goes through another spoke. To get from the
hub to any point on the rim you travel exactly one spoke.

In SQL terms: from `fact_sales` you reach any customer, product or date
attribute with exactly **one join**.

---

## 4. E-commerce example

The project brief's three classic questions map to the star like this:

```text
fact_sales + dim_product    →  revenue by category
fact_sales + dim_customer   →  revenue by region
fact_sales + dim_date       →  monthly revenue
```

And combinations are just more spokes:

```text
fact_sales + dim_date + dim_product   →  monthly revenue by category
```

Alice's order 3226 would sit in the middle like this:

```text
          dim_date: 20260115 → 2026-01-15, Thursday, January, Q1, 2026
                         │
dim_customer ─────── fact_sales ─────── dim_product
Alice, HCMC,         2 rows:             Laptop 14-inch, Computers, Nimbus
South, premium       laptop  1263.85     Wireless Mouse, Computers, Keystone
                     mice      50.00
```

---

## 5. Diagram (candidate design)

```text
                         ┌───────────────────┐
                         │     dim_date      │
                         │ date_key          │
                         │ full_date, day,   │
                         │ month, quarter,   │
                         │ year, is_weekend  │
                         └─────────┬─────────┘
                                   │
┌───────────────────┐    ┌─────────┴─────────┐    ┌───────────────────┐
│   dim_customer    │    │    fact_sales     │    │    dim_product    │
│ customer_key      ├────┤ date_key          ├────┤ product_key       │
│ customer_id       │    │ customer_key      │    │ product_id, sku   │
│ name, city,       │    │ product_key       │    │ product_name,     │
│ region, segment   │    │ quantity, ...     │    │ category, brand   │
└───────────────────┘    │ net_amount        │    └───────────────────┘
                         └───────────────────┘
```

This is the starting proposal from the brief. Treat each box as something to
argue about in Phase 3, not as a finished design.

---

## 6. Official terminology

| Term | Plain meaning |
| --- | --- |
| **Star schema** | One fact table joined directly to several dimension tables |
| **Snowflake schema** | Dimensions split further into sub-tables (e.g. `dim_product` → `dim_category`), so some lookups need two hops |
| **Denormalised** | Repeating descriptive values (every Computers product row says "Computers") to avoid extra joins |
| **Natural key** (business key) | The id from the source system: `customer_id`, `product_id`, `sku` |
| **Surrogate key** | A new id created by the warehouse, meaning nothing outside it: `customer_key` |
| **Foreign key** | A fact column that points at a dimension's key |
| **Date dimension** | A pre-built calendar table, one row per day |

### Natural key vs surrogate key (an open question for you)

Why not just put `customer_id` on the fact table and join on it? Often you
could. Things to weigh in Phase 3:

```text
Natural key (customer_id)                 Surrogate key (customer_key)
- already exists, easy to understand      - controlled by the warehouse
- breaks if two sources reuse the         - survives a source system migration
  same ids                                - lets one customer have several
- one row per customer, forever             historical versions (Phase 7)
                                          - one more column to generate
```

The surrogate-key argument becomes strongest with history tracking, covered in
Phase 7. For a
first version, you will decide whether that benefit is worth it now.

### Why a date dimension when `ordered_at` already has a date?

Because a raw date carries hidden information that every query would otherwise
recompute:

```text
2026-01-15   →   Thursday, January, Q1, 2026, weekday
```

With `dim_date`, "revenue on weekends in Q4" becomes a simple filter instead
of a pile of date functions. It also gives you a row for **every** day, even
days with zero sales, which matters for charts.

---

## 7. Small SQL example

### 7a. Runs today: what a `dim_date` row could look like

This query needs no tables at all. DuckDB generates seven days around Alice's
order:

```sql
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key,
    d::DATE                                AS full_date,
    dayname(d)                             AS day_name,
    monthname(d)                           AS month_name,
    quarter(d)                             AS quarter,
    year(d)                                AS year,
    isodow(d) IN (6, 7)                    AS is_weekend
FROM range(DATE '2026-01-12', DATE '2026-01-19', INTERVAL 1 DAY) AS t(d);
```

Try it:

```bash
make query SQL="SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key, d::DATE AS full_date, dayname(d) AS day_name, monthname(d) AS month_name, quarter(d) AS quarter, year(d) AS year, isodow(d) IN (6, 7) AS is_weekend FROM range(DATE '2026-01-12', DATE '2026-01-19', INTERVAL 1 DAY) AS t(d)"
```

Line by line:

- `range(start, end, INTERVAL 1 DAY)` — produces one value per day, from the
  start up to (not including) the end. `AS t(d)` names the column `d`.
- `strftime(d, '%Y%m%d')` — formats the date as text `20260115`; `CAST(... AS
  INTEGER)` turns it into the number 20260115. A readable integer is a common
  choice for `date_key`.
- `d::DATE` — `range` returns timestamps; this keeps only the date part.
- `dayname`, `monthname`, `quarter`, `year` — DuckDB date functions that
  produce the attributes analysts group by.
- `isodow(d) IN (6, 7)` — ISO day of week: Monday = 1 ... Sunday = 7, so 6 and
  7 are the weekend. The result is a boolean.

You should see 2026-01-15 as Thursday, January, quarter 1.

### 7b. Future, illustrative only: a question against the star

The tables below **do not exist yet**. This is what the query would look like
once they do:

```sql
-- FUTURE (Phase 3/4): fact_sales, dim_date and dim_product do not exist yet.
SELECT
    d.year,
    d.month,
    p.category,
    SUM(f.net_amount) AS revenue
FROM fact_sales  AS f
JOIN dim_date    AS d ON d.date_key    = f.date_key
JOIN dim_product AS p ON p.product_key = f.product_key
GROUP BY d.year, d.month, p.category
ORDER BY d.year, d.month, revenue DESC;
```

Line by line:

- `FROM fact_sales AS f` — always start from the fact: it defines what one row
  is (one sold product line) and holds the numbers.
- `JOIN dim_date ...` / `JOIN dim_product ...` — one hop each, on a key. Each
  fact row matches exactly one date row and one product row, so the join adds
  columns without adding rows.
- `SUM(f.net_amount)` — an additive measure, safe to sum.
- `GROUP BY d.year, d.month, p.category` — the dimension attributes decide the
  rows of the answer.
- Notice what is missing: no status filter, no price formula. Those decisions
  were made **once**, when `fact_sales` was built. That is the point of the
  model.

---

## 8. Common beginner mistakes

- **Adding dimensions because they are common.** `dim_payment_method`,
  `dim_store`, `dim_promotion` sound professional. Add one only when a real
  question needs it and the grain supports it.
- **Snowflaking too early.** Splitting `category` into its own table saves
  almost nothing here and adds a join to every category question.
- **Joining fact to fact.** Joining a future payments fact to `fact_sales` on
  `order_id` fans out, exactly like joining `raw.payments` to
  `raw.order_items` does: order 1001 has 2 lines × 2 payments = 4 rows.
- **A dimension with duplicate keys.** If `dim_product` has two rows for the
  same product, every sale of that product joins twice and its revenue doubles.
  In Phase 5 you'll add a `unique` test that catches it.
- **Taking measures from a dimension.** `dim_product.list_price` is a
  description of the product today, not the price that was paid.
- **Using natural keys everywhere without thinking.** It works until a source
  reuses an id or you need history; know what you are giving up.

---

## 9. Small exercise

1. On paper, draw your own star for our shop. Do not copy the diagram above;
   start from the grain you chose at the Phase 2 checkpoint.
2. For each question, list the fact and the dimensions you need:

   ```text
   a) Which regions generate the most revenue?
   b) How many products are sold each month?
   c) Which brands sell best on weekends?
   d) What is the revenue of premium-segment customers per quarter?
   ```

3. `payments.payment_method` (credit card, e-wallet, ...) is descriptive. Should
   it become an attribute of `fact_sales`, a new dimension, or something else?
   Think about the grain of payments versus the grain of `fact_sales`.
4. Decide, with a reason, whether your first version uses surrogate keys.

<details><summary>Hint</summary>

For 3: an order can have zero payment rows (cash on delivery not yet
delivered), one, or several (a failed attempt, then a success, maybe a refund).
How many payment methods can a single product line have? What happens to the
grain if you attach them?

For 4: there is no single right answer. A good answer names the benefit you
would get now, and the cost you would pay now.

</details>

---

## 10. Before continuing, I should be able to explain:

```text
□ What a star schema is and why it is shaped for reading, not writing
□ Why each dimension is one join away from the fact
□ The difference between a star and a snowflake schema
□ The difference between a natural key and a surrogate key, with one trade-off
□ Why dim_date exists when ordered_at already holds a date
□ How 2026-01-15 becomes Thursday, January, Q1, 2026
□ Why a duplicate key in a dimension inflates revenue
□ Which dimensions "revenue by region per month" needs
□ My own draft of the star, with the grain written on top
```

---

**Next →** [Phase 4 · Lesson 1 — ETL vs ELT](phase-4-lesson-1-etl-vs-elt.md)
