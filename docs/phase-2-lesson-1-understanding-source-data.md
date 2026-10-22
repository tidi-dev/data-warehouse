# Phase 2 · Lesson 1 — Understanding the Source Data

> **Phase 2 · Lesson 1 of 2.** Before modeling anything, we get to know the
> data the shop actually produces. Do this lesson with the warehouse open
> (TablePlus or `make query`).

---

## 1. What problem are we solving?

Every warehouse mistake that matters starts here: someone assumes they know
what a table contains, and they're wrong. "Revenue" gets taken from the wrong
column, a join silently doubles rows, cancelled orders are counted.

So before designing a single warehouse table we answer, for each source
table:

```text
What is this table FOR, in the running business?
What does one row stand for?
Which column identifies a row?
How does it connect to the other tables?
What surprises are hiding in it?
```

---

## 2. Plain-English explanation

The source tables were designed by the shop's developers to **operate the
shop**: save a checkout safely, show a customer their orders, record what
the payment provider said. They were **not** designed to answer "revenue by
category by month". That's not a flaw — it's a different job
(OLTP vs OLAP, from Phase 1).

> Source-system structure is optimized for operating the business, not
> necessarily for answering analytical questions.

---

## 3. Real-world analogy

A shop's paperwork: a **customer card file**, a **product price list**, a
pile of **receipts** (one per checkout, listing several items), and the
**card terminal printout** (every attempt, decline and refund). Each was
designed for a clerk's job. To find out "how much did we earn from
cookware last spring?" you'd have to combine receipts with the price list
and ignore the refunded ones. Same here.

---

## 4. Get the data in front of you

You loaded the warehouse in Phase 1 · Lesson 2. Check it's still there:

```bash
make query             # lists the tables — you should see five in schema raw
```

(Empty? Run `make generate-data` and then `make load` — disconnect TablePlus
first.)

Look at the tables in TablePlus under schema **`raw`**, or peek with
`make query`:

```bash
make query SQL="SELECT * FROM raw.orders LIMIT 5"
```

> **Why `raw`?** It's the untouched copy of the source, exactly as the shop
> gave it to us. The only additions are two bookkeeping columns on every
> table — `_source_file` (which CSV it came from) and `_loaded_at` (when).
> We'll talk about layers (raw → staging → marts) in Phase 4.

---

## 5. The relationships (diagram)

```text
                  ┌─────────────┐
                  │  customers  │  800 rows
                  │ customer_id │
                  └──────┬──────┘
                         │ one customer places many orders
                         ▼
┌─────────────┐   ┌─────────────┐        ┌─────────────┐
│  products   │   │   orders    │───────►│  payments   │  4,824 rows
│ product_id  │   │  order_id   │  one   │ payment_id  │
│   60 rows   │   │ 4,429 rows  │  order │  order_id   │
└──────┬──────┘   └──────┬──────┘  has   └─────────────┘
       │                 │         0..n payment events
       │                 │ one order has many lines
       │                 ▼
       │          ┌──────────────┐
       └─────────►│ order_items  │  8,398 rows
  one product     │order_item_id │
  appears in many │  order_id    │
  lines           │  product_id  │
                  └──────────────┘
```

The column schema for every table lives in one place:
[`scripts/source_schema.py`](../scripts/source_schema.py).

---

## 6. Table by table

### `customers` — the customer card file

| Column | Meaning |
|---|---|
| `customer_id` | The shop's id for the account (**primary key**) |
| `first_name`, `last_name`, `email` | Who they are |
| `city`, `region` | Where they live **now** (North / Central / South Vietnam) |
| `customer_segment` | `standard`, `premium` or `business` — **now** |
| `created_at` | When the account was created |
| `updated_at` | When the profile was last edited |

**What it's for in the shop:** log in, ship parcels to the right address,
show the right prices to business customers.

**Surprise #1 — only the present exists.** 134 of the 800 customers have
`updated_at > created_at`: they changed something (maybe moved city). The
old values are **gone** — the website simply overwrote them. Remember Alice
(`customer_id = 1`, Ho Chi Minh City); she'll move later in the course and
we'll have to decide what that means for her old purchases
(Phase 7).

**Surprise #2 — not every customer buys.** 116 customers have an account but
no orders. "Number of customers" depends on what you count.

### `products` — the price list

| Column | Meaning |
|---|---|
| `product_id` | Primary key |
| `sku` | Stock-keeping unit code, e.g. `COMP-0011` |
| `product_name`, `category`, `brand` | What it is (6 categories) |
| `list_price` | The price **today** |
| `is_active` | `false` = discontinued (not sold any more) |
| `created_at`, `updated_at` | Launched / last changed |

**What it's for:** show the catalog and today's price on the website.

**Surprise #3 — today's price is not yesterday's price.** About a third of
the products got more expensive on 2026-01-01. `list_price` only shows the
new price. The price a customer *actually paid* is stored elsewhere
(`order_items.unit_price`). Using `list_price` to compute past revenue would
be wrong.

### `orders` — one checkout

| Column | Meaning |
|---|---|
| `order_id` | Primary key (starts at 1001) |
| `customer_id` | Who placed it (**foreign key** → `customers`) |
| `order_status` | `pending` → `shipped` → `completed`, or `cancelled` |
| `order_total` | Total of the order's lines, copied onto the header for convenience |
| `ordered_at` | When the customer checked out |
| `updated_at` | When the status last changed |

**What it's for:** show "My orders", drive the warehouse picking process,
track delivery.

**Surprise #4 — status changes over time.** The export was taken at
midnight on 1 October 2026. Orders from the last days of September are
still `pending` or `shipped`; they may become `completed` — or `cancelled`
— after the export. Counts in this export:

```text
completed  3,952     cancelled  403     shipped  52     pending  22
```

Whether a `shipped` or `cancelled` order "counts as revenue" is a
**business decision**, not a technical one.

### `order_items` — the lines on the receipt

| Column | Meaning |
|---|---|
| `order_item_id` | Primary key |
| `order_id` | Which order this line belongs to (FK → `orders`) |
| `product_id` | Which product (FK → `products`) |
| `quantity` | How many units |
| `unit_price` | Price per unit **at the moment of purchase** |
| `discount_amount` | Discount for the **whole line** (not per unit) |

Money for one line:

```text
line amount = quantity × unit_price − discount_amount
```

**What it's for:** record exactly what was bought, at what price, so the
shop can ship it and handle returns.

Lines per order today:

```text
1 line   1,973 orders
2 lines  1,373 orders
3 lines    653 orders
4 lines    430 orders
```

### `payments` — the card-terminal printout

| Column | Meaning |
|---|---|
| `payment_id` | Primary key |
| `order_id` | Which order (FK → `orders`) |
| `payment_method` | `credit_card`, `e_wallet`, `bank_transfer`, `cash_on_delivery` |
| `payment_status` | `succeeded`, `failed` or `refunded` |
| `amount` | Amount of this payment event |
| `processed_at` | When the payment provider processed it |

**What it's for:** reconcile with the payment provider, issue refunds,
answer "did this customer pay?".

**Surprise #5 — payments are events, not "the payment of the order".**

```text
payments per order:   0 → 119 orders   (cash on delivery not collected yet, or cancelled)
                      1 → 3,815 orders
                      2 →   476 orders  (a failed attempt then success, or paid then refunded)
                      3 →    19 orders  (failed, succeeded, refunded)
```

Summing `payments.amount` blindly would count failed attempts and refunds
as money received.

---

## 7. A concrete order, end to end

Alice's order from 15 January 2026 (try it!):

```bash
make query SQL="SELECT o.order_id, o.order_status, o.order_total, p.product_name, oi.quantity, oi.unit_price, oi.discount_amount FROM raw.orders o JOIN raw.order_items oi USING (order_id) JOIN raw.products p USING (product_id) WHERE o.customer_id = 1 AND o.ordered_at = '2026-01-15 20:30:00'"
```

```text
order_id  order_status  order_total  product_name    quantity  unit_price  discount_amount
3226      completed     1313.85      Laptop 14-inch  1         1263.85     0.00
3226      completed     1313.85      Wireless Mouse  2           25.00     0.00
```

Notice: the **order** facts (`order_id`, `order_status`, `order_total`) are
repeated on both lines, because the join produced one row per *line*. Keep
that observation — it is the whole topic of the next lesson.

---

## 8. Line by line (the query above)

| Part | Meaning |
|---|---|
| `FROM raw.orders o` | Start with order headers; `o` is a short alias |
| `JOIN raw.order_items oi USING (order_id)` | Attach each order's lines. `USING (order_id)` = "match on the column with this name in both tables" |
| `JOIN raw.products p USING (product_id)` | Attach the product name to each line |
| `WHERE o.customer_id = 1 AND o.ordered_at = ...` | Only Alice's order at that moment |

---

## 9. Common beginner mistakes

- **Using `products.list_price` for revenue.** It's today's price. Use the
  price recorded at the time of sale (`order_items.unit_price`).
- **Treating `payments` as "one payment per order".** It's one row per
  payment *event*: failures and refunds included.
- **Assuming every order is final.** Status changes; recent orders aren't
  done yet.
- **Forgetting the discount is per line, not per unit.**
- **Assuming history exists.** The source only knows each customer's and
  product's *current* values.
- **Using the operational schema directly for every analytical question.**
  Each analyst would have to rediscover all five surprises above.

---

## 10. Exercise — write the "one row =" sentence

For each table, write one sentence of the form
**"One row in `<table>` represents …"**. Be precise: *one what?*

```text
customers    →
products     →
orders       →
order_items  →
payments     →
```

Then check yourself with SQL. If your sentence says "one X per Y", the
column(s) that identify that must be unique. For example, to check that
`customer_id` is unique in `customers`:

```bash
make query SQL="SELECT count(*) AS rows, count(DISTINCT customer_id) AS distinct_ids FROM raw.customers"
```

If `rows = distinct_ids`, no customer appears twice.

<details><summary>Hint for order_items</summary>

Is there ever more than one row for the same `order_id`? Is there ever more
than one row for the same `(order_id, product_id)` pair? Try
`count(DISTINCT (order_id, product_id))`.

</details>

<details><summary>Hint for payments</summary>

Look at all payment rows for `order_id = 1001`. Are they "the payment" or
something else?

</details>

---

## 11. Before continuing, I should be able to explain:

```text
□ What each of the five tables is FOR in the running shop.
□ What one row in customers represents.
□ What one row in orders represents.
□ What one row in order_items represents.
□ Why products.list_price is the wrong price for past revenue.
□ Why payments can have 0, 1, 2 or 3 rows for one order.
□ Which information the source system has already thrown away.
```

---

**Next →** [Phase 2 · Lesson 2 — Grain](phase-2-lesson-2-grain.md)
