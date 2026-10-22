# Phase 2 · Lesson 2 — Grain: What Exactly Does ONE Row Represent?

> **Phase 2 · Lesson 2 of 2 — the last lesson of the first milestone.** It ends with *you*
> proposing the grain of our future `fact_sales` table. Then we stop.

---

## 1. What problem are we solving?

Look at what happened in the last lesson when we joined Alice's order to
its lines: `order_total = 1313.85` appeared **twice**. Now imagine summing
that column:

```bash
make query SQL="SELECT sum(o.order_total) AS summed_after_join FROM raw.orders o JOIN raw.order_items oi USING (order_id)"
```

```text
Real total of all orders:            1,194,379.79
Sum of order_total after the join:   2,894,749.05     ← 2.4× too much!
```

No error. No warning. Just a wrong number that looks plausible. This is the
most common way analytics goes wrong, and it comes from not knowing — or
mixing — **what one row represents**.

---

## 2. Plain-English explanation

> **Grain** = the answer to "what exactly does ONE row in this table
> represent?"

You should be able to finish this sentence for every table you touch:

```text
"One row in <table> = one <thing>."
```

Examples from our shop:

```text
customers     one row  =  one customer account
orders        one row  =  one order (one checkout)
```

You wrote sentences like these yourself in the exercise at the end of the
previous lesson. Keep them next to you.

---

## 3. Real-world analogy

A supermarket receipt.

```text
┌──────────────────────────────┐
│  RECEIPT #1001               │  ← the receipt  = one order
│  ----------------------------│
│  Daily Moisturizer  2 × 26.00│  ← one line     = one order item
│  Laptop 16" Pro     1 × 1799 │  ← one line     = one order item
│  ----------------------------│
│  TOTAL            1,851.00   │  ← belongs to the RECEIPT, not to a line
└──────────────────────────────┘
```

"How many receipts today?" — count receipts.
"How many laptops today?" — count lines.
If you write the **total** onto every line and then add up the lines, you've
counted the receipt's total twice. Grain is simply being careful about
*which level* a number lives at.

---

## 4. E-commerce example: the same order at three grains

Order 1001 (the very first order in our data):

```text
orders (grain: one order)                1 row
┌──────────┬─────────────┐
│ order_id │ order_total │
│ 1001     │ 1851.00     │
└──────────┴─────────────┘

order_items (grain: one product line in one order)     2 rows
┌──────────┬────────────┬──────────┬────────────┐
│ order_id │ product_id │ quantity │ unit_price │
│ 1001     │ 53         │ 2        │   26.00    │
│ 1001     │ 12         │ 1        │ 1799.00    │
└──────────┴────────────┴──────────┴────────────┘

payments (grain: one payment event)       2 rows
┌──────────┬────────────────┬─────────┐
│ order_id │ payment_status │ amount  │
│ 1001     │ failed         │ 1851.00 │
│ 1001     │ succeeded      │ 1851.00 │
└──────────┴────────────────┴─────────┘
```

Now join all three on `order_id`:

```text
orders ⋈ order_items ⋈ payments  for order 1001   →   2 lines × 2 payments = 4 rows

order_id  order_total  product_id  quantity  payment_status
1001      1851.00      53          2         succeeded
1001      1851.00      12          1         succeeded
1001      1851.00      53          2         failed
1001      1851.00      12          1         failed
```

Every number is now repeated. `sum(quantity)` says 6 units were sold
(really 3). `sum(order_total)` says 7,404 (really 1,851). This multiplication
of rows is called **fan-out**.

---

## 5. Diagram

```text
               finer (more rows, more detail)
                          ▲
   payments ⋈ items       │   4 rows for order 1001  ← mixed grain: DANGER
   order_items            │   2 rows                 ← one line in one order
   orders                 │   1 row                  ← one order
   customers              │   (Alice: 1 row, many orders)
                          ▼
               coarser (fewer rows, less detail)
```

You can always go **up** (coarser) by aggregating:
lines → `SUM` → orders → `SUM` → customers.

You can **never** go down: from `order_total` alone you can't recover which
products were bought.

---

## 6. Official terminology

| Term | Plain English |
|---|---|
| **Grain** | What one row represents. |
| **Atomic grain** | The finest, most detailed level available (e.g. one order line). |
| **Fan-out** | A join that multiplies rows, because one row on one side matches many on the other. |
| **Double counting** | Summing a number that fan-out has repeated. |
| **Cardinality** | How many rows match: one-to-one, one-to-many (one order → many lines), many-to-many. |
| **Primary key** | The column(s) whose value is unique per row — the grain expressed as columns. |

The grain and the primary key go together:

```text
grain: one order                     → key: order_id
grain: one product line in an order  → key: order_item_id
                                        (and (order_id, product_id) is also unique)
```

---

## 7. Small SQL example — testing a grain

A grain statement is a claim. Claims can be tested:

```sql
SELECT
    count(*)                               AS row_count,
    count(DISTINCT order_item_id)          AS distinct_lines,
    count(DISTINCT order_id)               AS distinct_orders,
    count(DISTINCT (order_id, product_id)) AS distinct_order_product_pairs
FROM raw.order_items;
```

```bash
make query SQL="SELECT count(*) AS row_count, count(DISTINCT order_item_id) AS distinct_lines, count(DISTINCT order_id) AS distinct_orders, count(DISTINCT (order_id, product_id)) AS distinct_order_product_pairs FROM raw.order_items"
```

```text
row_count  distinct_lines  distinct_orders  distinct_order_product_pairs
8398       8398            4429             8398
```

## 8. Line by line

| Line | What it tells us |
|---|---|
| `count(*)` | 8,398 rows in total |
| `count(DISTINCT order_item_id)` = 8,398 | `order_item_id` is unique → it can be the key |
| `count(DISTINCT order_id)` = 4,429 | Fewer than rows → one order has *several* rows. The grain is **not** "one order" |
| `count(DISTINCT (order_id, product_id))` = 8,398 | Each product appears at most once per order → "one product line in one order" holds |

`(order_id, product_id)` builds a pair (a *row value*), so `DISTINCT`
compares the two columns together.

---

## 9. Choosing the grain of `fact_sales`

Soon (Phase 3) we will design a table to answer most of the CEO's
questions. It will hold **sales**. Before deciding *any* of its columns, we
must decide what one row means.

A likely candidate:

```text
ONE ROW  =  ONE PRODUCT LINE purchased as part of ONE COMPLETED ORDER
```

**Don't accept this because it's written here.** Test it against the
questions we need to answer:

```text
Question                                   Needs to know...           At line grain?
-----------------------------------------  -------------------------  --------------
Revenue this month                         money, date                 ?
Revenue by product / by category           money, product              ?
Units sold per month                       quantity, date              ?
Revenue by region                          money, customer             ?
Average order value                        money, number of orders     ?
New customers per month                    customer, first date        ?
```

And think about the alternatives:

```text
Option A: one row = one order              (like raw.orders)
Option B: one row = one product line       (like raw.order_items)
Option C: one row = one payment event      (like raw.payments)
```

### Exercise — propose the grain (this is the milestone's goal)

Write your answers down (a text file, a notebook, or paper):

1. Fill in the "At line grain?" column above. For each question: can it be
   answered from a table at the line grain? How?
2. Why might Option A (one order per row) be a bad choice for "revenue by
   category"? Use Alice's order as an example.
3. Why might Option C (payments) be a bad base for *sales* analysis? Use
   order 1001 as an example.
4. The candidate says "completed order". Which `order_status` values should
   count as a sale: `completed`? `shipped`? `pending`? `cancelled`? What
   would change for the business if you included `shipped`?
5. Write your **final grain statement** for `fact_sales` in one sentence,
   and name the column(s) that would be unique per row.

<details><summary>Hint for 1</summary>

From line-level rows you can always *aggregate up*. "Average order value"
needs "number of orders" — can you count distinct orders from line rows?

</details>

<details><summary>Hint for 2</summary>

Alice's order 3226 has a laptop (Computers) and a mouse (Computers) — but
plenty of orders mix categories. Which category would an order-level row
belong to?

</details>

<details><summary>Hint for 3</summary>

Does a payment row know which *products* it paid for? What happens to
failed attempts and refunds?

</details>

<details><summary>Hint for 4</summary>

There's no single right answer: it's a business definition. Think about
what finance would say about money for an order that might still be
cancelled, and about recent months looking artificially low.

</details>

There is no answer key on purpose. Bring your answers to the Data
Warehouse Tutor (start it with `claude --agent data-warehouse-tutor`) or
to a review session, and we'll discuss them before Phase 3.

---

## 10. Common beginner mistakes

- **Not defining the grain.** Starting with "which columns do we need?"
  instead of "what is one row?".
- **Mixing grains in one table.** Putting `order_total` (order level) on
  every line row invites someone to `SUM` it.
- **Double counting after joins.** Joining `payments` to `order_items` and
  summing anything.
- **Choosing a coarse grain "because it's smaller".** You can aggregate a
  fine grain up; you can't split a coarse grain down.
- **Confusing the key with the grain.** The key is how you *check* the
  grain, not a replacement for the sentence.

---

## 11. Before continuing, I should be able to explain:

```text
□ What does grain mean?
□ What does one row in customers represent?
□ What does one row in orders represent?
□ What does one row in order_items represent?
□ What does one row in payments represent — and why is it not "one payment per order"?
□ What is fan-out, and why did sum(order_total) come out 2.4× too high?
□ How can I test a grain statement with SQL?
□ What grain might fact_sales use — and why that one rather than one order per row?
```

---

## STOP HERE

This is the end of the first milestone. Do **not** move on to building
facts and dimensions yet. Next steps, together:

1. Answer the exercise in section 9 and the checklist above.
2. Review your answers with the Data Warehouse Tutor.
3. Only then click Next.

---

**Next → (only after your checkpoint review)** [Phase 3 · Lesson 1 — Facts and dimensions](phase-3-lesson-1-facts-and-dimensions.md)
