# Phase 6 · Lesson 1 — Analytical SQL: From Business Question to Answer

> **Preview — Phase 6 · Lesson 1 of 1.** Read this to understand the idea. Do not build anything from this page yet; we implement it together in Phase 6.

One exception: the worked example in section 7 runs **today** against
the `raw` tables, and the exercises can be attempted on `raw` too. Later,
once `fact_sales` and the `dim_*` tables exist (future — they do not
exist yet), you will redo them in a much simpler form.

---

## 1. What problem are we solving?

The CEO walks up and asks: *"How much revenue did we make each month?"*

You know SQL, so it is tempting to start typing `SELECT sum(...)`. But
sum *of what*, from *which table*, counting *which orders*? Most wrong
numbers in analytics come from skipping those questions, not from SQL
syntax errors.

This lesson is about a **repeatable thinking process** that turns a
business question into correct SQL. The SQL itself is usually the easy
part.

---

## 2. Plain-English explanation

Before writing any SQL, answer these in order:

```text
Business question     "Revenue per month"
       ↓
Which fact?           Which table has one row per thing I'm adding up?
       ↓
Which dimensions?     What do I want to slice by? (month, category, region...)
       ↓
Which measure?        Which number do I add / count / average?
       ↓
Which joins?          Which tables must I connect, and could a join duplicate rows?
       ↓
Which grouping?       What goes in GROUP BY? What filters apply?
       ↓
SQL
```

If you can fill in every line in plain English, the SQL almost writes
itself. If you can't, no amount of SQL skill will save the answer.

---

## 3. Real-world analogy

A recipe. "Make a cake" is the business question. Before you turn on the
oven you decide: which ingredients (fact and dimensions), how much of
each (measures), in what order to combine them (joins), and how to slice
it at the end (grouping). Throwing everything in a bowl at once
sometimes works. Usually it doesn't.

---

## 4. E-commerce example: what do we "add up"?

Alice's January order (order 3226 in our generated data):

```text
raw.orders          order_id 3226   order_total 1313.85   status completed

raw.order_items     order 3226   Laptop 14-inch   qty 1   unit_price 1263.85   discount 0.00
                    order 3226   Wireless Mouse   qty 2   unit_price   25.00   discount 0.00
```

Revenue for a line = `quantity * unit_price - discount_amount`
(the line's net amount). Here: `1263.85 + 50.00 = 1313.85`, which
matches the header's `order_total`.

So we have two places that "contain" revenue: the header total (one per
order) and the line amounts (one per product line). Which one we use
depends on the question:

- Revenue **per month** — either works.
- Revenue **per product or category** — only the lines know which product
  earned what. `order_items` is closest to the grain we need (one row = one product
  line in one order).

---

## 5. Diagram

```text
             raw.customers           raw.products
             (who, region)           (what, category)
                   ▲                       ▲
                   │ customer_id           │ product_id
                   │                       │
             raw.orders ◄─── order_id ─── raw.order_items
           (when, status)                 (qty, unit_price, discount)
           ONE row per order              MANY rows per order

  Later (future):    dim_customer ◄── fact_sales ──► dim_product
                                         │
                                         ▼
                                      dim_date
```

---

## 6. Official terminology

| Term | Plain meaning |
|---|---|
| **Measure** | A number stored on a fact row that you aggregate: `quantity`, line net amount. |
| **Metric** | A business-defined calculation built from measures: revenue, average order value, growth %. |
| **Additive measure** | Can be summed across any dimension (quantity, revenue). |
| **Non-additive** | Must not be summed: averages, ratios, distinct counts. Recompute them from their parts. |
| **Fan-out** | A join that multiplies rows (one order → many lines), silently inflating sums. |
| **Aggregation** | `sum`, `count`, `avg`... combined with `GROUP BY`. |

---

## 7. Worked example (runs today): monthly revenue

Reasoning first:

```text
Business question   Monthly revenue
Which fact?         raw.order_items (one row per product line) — today's stand-in for fact_sales
Which dimensions?   Month, taken from raw.orders.ordered_at
Which measure?      Line net = quantity * unit_price - discount_amount
Which joins?        order_items -> orders on order_id (many lines to one order: safe,
                    because we sum a LINE-level measure)
Which grouping?     Group by month; filter to completed orders
```

The SQL:

```bash
make query SQL="
SELECT
    CAST(date_trunc('month', o.ordered_at) AS DATE)          AS order_month,
    count(DISTINCT o.order_id)                               AS orders,
    sum(oi.quantity * oi.unit_price - oi.discount_amount)    AS revenue
FROM raw.orders AS o
JOIN raw.order_items AS oi
    ON oi.order_id = o.order_id
WHERE o.order_status = 'completed'
GROUP BY order_month
ORDER BY order_month
"
```

You should see 21 rows, January 2025 to September 2026, starting with
roughly 106 orders and 30,608.55 of revenue in January 2025.

### Line by line

- `CAST(date_trunc('month', o.ordered_at) AS DATE)` — `date_trunc` turns
  `2026-01-15 20:30:00` into `2026-01-01 00:00:00`, so every order in a
  month gets the same value. The `CAST` drops the time part for
  readability.
- `count(DISTINCT o.order_id)` — after the join there is one row per
  *line*, so a plain `count(*)` would count lines. `DISTINCT` counts
  orders.
- `sum(oi.quantity * oi.unit_price - oi.discount_amount)` — the measure,
  computed per line then summed. `unit_price` is the price **at the time
  of sale**; never use `raw.products.list_price` (today's price) for
  historical revenue.
- `FROM raw.orders AS o JOIN raw.order_items AS oi ON oi.order_id = o.order_id`
  — orders gives us the date and status; order_items gives us the money.
- `WHERE o.order_status = 'completed'` — **this is a business decision,
  not a SQL decision.** Should `shipped` orders count? `pending`? Finance
  and marketing may answer differently. Notice that September 2026 looks
  weaker partly because its most recent orders are still `pending` or
  `shipped`. Write the rule down and use it consistently.
- `GROUP BY order_month` — one output row per month. DuckDB lets you
  group by the alias.
- `ORDER BY order_month` — chronological output.

---

## 8. Two warnings before you start

### Warning 1: double counting with `order_total`

`order_total` lives on the **order** (one per order). If you join
`order_items` and then sum `order_total`, each order's total is repeated
once per line. Alice's 1313.85 becomes 2627.70. Try it — this runs today:

```bash
make query SQL="
SELECT
    (SELECT sum(order_total) FROM raw.orders WHERE order_status = 'completed') AS correct,
    sum(o.order_total) AS inflated_by_join
FROM raw.orders AS o
JOIN raw.order_items AS oi ON oi.order_id = o.order_id
WHERE o.order_status = 'completed'
"
```

The "inflated" number is about 2.4 times the correct one. No error, no
warning — just a wrong answer. Rule: **sum a measure only at its own
grain.** Header amounts from the header table, line amounts from the line
table.

### Warning 2: average order value

Average order value (AOV) = **total revenue / number of orders**.

It is **not** `avg(quantity * unit_price - discount_amount)` over
`order_items` — that is the average *line* value. Alice's order has two
lines; her order value is 1313.85, but the average of her lines is
656.93. Across all completed orders, the wrong method gives roughly half
the right answer. Averages are non-additive: compute them from a sum and
a count.

---

## 9. Exercises

For each one, fill in the reasoning template **on paper first**, then
write the SQL against `raw`. Use `completed` orders unless the exercise
says otherwise. Answers are deliberately not given — bring your attempt
to the Phase 6 session for review.

```text
Business question:
Which fact?
Which dimensions?
Which measure?
Which joins?          (could any join multiply rows?)
Which grouping?       (and which filters?)
```

**E1. Monthly revenue, your way.** Change the worked example so `shipped`
orders also count. Which months change the most, and why?

<details><summary>Hint</summary>
Only the WHERE clause changes. Look at the last few months.
</details>

**E2. Top 10 products by revenue.**

<details><summary>Hint</summary>
Dimension: product. You need raw.products for the name, raw.orders for
the status. ORDER BY ... DESC LIMIT 10.
</details>

**E3. Revenue by category.**

<details><summary>Hint</summary>
Same joins as E2; only the grouping column changes.
</details>

**E4. Average order value per month.**

<details><summary>Hint</summary>
Re-read Warning 2. You need two numbers per month — a sum and a distinct
count — then divide one by the other.
</details>

**E5. Monthly active customers** (customers with at least one completed
order that month).

<details><summary>Hint</summary>
Do you even need order_items here? The measure is a count of something
distinct.
</details>

**E6. New customers per month.**

<details><summary>Hint</summary>
First decide what "new" means: the month of `raw.customers.created_at`
(signed up), or the month of their first completed order (first
purchase)? Both are valid; they give different numbers. For the second,
think `min(ordered_at)` per customer, then group.
</details>

**E7. Revenue by region.**

<details><summary>Hint</summary>
region lives on raw.customers. Which region does that column hold — the
one at the time of the sale, or today's? Remember: the source keeps only each
customer's *current* values. Write one sentence about what your number really means.
</details>

**E8. Units sold by category.**

<details><summary>Hint</summary>
The measure is quantity, not money. Is quantity additive?
</details>

**E9. Month-over-month revenue growth (%).**

<details><summary>Hint</summary>
Start from the worked example as a CTE. Then look up the window function
`lag(revenue) OVER (ORDER BY order_month)`. Growth = (this month − last
month) / last month. What should the first month show?
</details>

---

## 10. Common beginner mistakes

- **Writing SQL before deciding the grain** of the answer and of the
  tables involved.
- **Double-counting after joins** — summing `order_total` after joining
  `order_items`, or joining `payments` (several events per order) and
  summing amounts.
- **Averaging lines instead of orders** for AOV.
- **Using `list_price` for historical revenue** instead of `unit_price`.
- **Forgetting the status filter**, so cancelled orders count as revenue.
- **Summing non-additive numbers**, such as adding up monthly averages or
  monthly distinct customer counts to get a yearly figure.
- **Treating payments as revenue** without thinking: a refund is a
  separate `refunded` row, and `failed` attempts are not money.
- **Not sanity-checking.** Compare your total with
  `SELECT sum(order_total) FROM raw.orders WHERE order_status = 'completed'`.

---

## 11. Before continuing, I should be able to explain:

```text
□ What are the six reasoning steps from business question to SQL?
□ Why is raw.order_items closer to the grain needed for revenue by product?
□ How is a line's revenue calculated, and why unit_price instead of list_price?
□ Why does summing order_total after joining order_items double-count?
□ Why is AOV = total revenue / number of orders, not an average of lines?
□ Why is "which statuses count as revenue" a business decision?
□ Which region does raw.customers.region describe — then or now?
□ What is the difference between a measure and a metric?
□ Given a business question, can I name the fact, dimensions, measures,
  joins and aggregation before writing SQL?   <── Phase 6 goal
```

---

**Next →** [Phase 7 · Lesson 1 — Slowly changing dimensions](phase-7-lesson-1-slowly-changing-dimensions.md)
