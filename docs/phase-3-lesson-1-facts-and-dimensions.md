# Phase 3 · Lesson 1 — Facts and Dimensions: "What Happened" vs "Who, What, When"

> **Preview — Phase 3 · Lesson 1 of 2.** Read this to understand the idea. Do not build anything from this page yet; we implement it together in Phase 3, after the Phase 2 grain checkpoint.

---

## 1. What problem are we solving?

Read these business questions out loud:

```text
How much revenue did we make this month?
Which categories generate the most revenue?
Which regions generate the most revenue?
How many products are sold each month?
```

Every one of them has the same shape:

```text
"a NUMBER we add up"   sliced by   "a DESCRIPTION we group or filter by"

   revenue                          month
   revenue                          category
   revenue                          region
   units sold                       month
```

In our source tables those two kinds of things are mixed together and spread
over five tables. The numbers live in `order_items`, the "when" lives in
`orders`, the "what" lives in `products`, the "who/where" lives in
`customers`. Every analyst would have to rediscover that, every time.

This lesson separates the two kinds of columns on purpose. That separation is
the core idea of dimensional modelling.

---

## 2. Plain-English explanation

Imagine every product purchased in every order becomes **one row in our sales
history**. Each row records *something that happened* and the numbers that
describe it: how many, at what price, how much discount, how much money.

Then, separately, we keep **reference lists** that describe the things
involved: a list of customers (name, city, region, segment), a list of
products (name, category, brand), and a calendar (day, month, quarter, year).

The sales history rows are long and thin and keep growing every day.
The reference lists are wide and descriptive and change slowly.

---

## 3. Real-world analogy

Think of a supermarket receipt and the shop's binders.

- Each **line on the receipt** is an event: "2 × milk, 1.20 each, 2.40". You
  can add receipt lines together: total spent, total items.
- The **product binder** says milk is in the *Dairy* aisle, brand *Vinamilk*.
- The **loyalty-card file** says the card belongs to someone in *Da Nang*.
- The **calendar** on the wall says the 15th was a *Thursday*.

You never add up the binder. You add up the receipt lines and use the binders
to decide *how to group* them ("spending on Dairy, by city, on weekends").

---

## 4. E-commerce example (real data)

Alice Nguyen (customer 1, Ho Chi Minh City) placed an order on 2026-01-15.
With the default seed (42) it is **order 3226**:

```text
Order #3226  (Alice, 2026-01-15 20:30)

Laptop 14-inch  × 1   @ 1263.85
Wireless Mouse  × 2   @   25.00
```

As rows in a sales-history table it would become:

```text
fact_sales (sketch)

order   product          quantity   unit_price   discount   net_amount
3226    Laptop 14-inch      1        1263.85       0.00      1263.85
3226    Wireless Mouse      2          25.00       0.00        50.00
```

And the descriptions those rows point to:

```text
product           category    brand        customer   city               region
Laptop 14-inch    Computers   Nimbus       Alice      Ho Chi Minh City   South
Wireless Mouse    Computers   Keystone
```

Notice the grain — the question from the Phase 2 checkpoint: one row = one
product line in one order. That is the grain of `raw.order_items`, which is why it is the
natural starting point.

---

## 5. Diagram

```text
             raw.orders ──────────── raw.order_items
             (when, who)              (how many, price)
                 │                          │
                 └────────────┬─────────────┘
                              ▼
                   ┌──────────────────────┐
                   │      fact_sales      │   numbers: quantity, net_amount ...
                   │ one row per order    │
                   │ line (proposal)      │
                   └──────────────────────┘
                     │        │         │
             points  │        │         │  points
                to   ▼        ▼         ▼  to
          dim_customer   dim_product   dim_date
          (WHO bought)   (WHAT sold)   (WHEN)
```

---

## 6. Official terminology

Now that the idea is concrete, here are the names:

| Term | Plain meaning | In our shop |
| --- | --- | --- |
| **Fact** | One event that happened, at a declared grain | One product line in one order |
| **Fact table** | The table of those events | `fact_sales` (future) |
| **Measure** | A number on the fact row that you aggregate | `quantity`, `net_amount` |
| **Dimension** | The context you group or filter by | customer, product, date |
| **Dimension table** | A table describing one kind of context | `dim_customer`, `dim_product`, `dim_date` |
| **Attribute** | One descriptive column on a dimension | `category`, `region`, `month_name` |
| **Key** | The column that links a fact row to a dimension row | `customer_key`, `product_key`, `date_key` |

A quick test you can apply to any column: *Would I ever SUM or AVG this?*
Then it is probably a measure. *Would I put it in GROUP BY or WHERE?* Then it
is probably a dimension attribute.

More definitions live in the [glossary](reference/glossary.md).

---

## 7. Measure additivity: which numbers can you safely add?

Not every number on a fact row behaves the same when you add it up.

**Additive** — summing across any dimension (product, customer, day) gives a
true answer.

```text
quantity     1 laptop + 2 mice = 3 units          -> meaningful
net_amount   1263.85 + 50.00   = 1313.85 revenue  -> meaningful
```

**Non-additive** — summing gives a number, but the number means nothing.

```text
unit_price   1263.85 + 25.00 = 1288.85            -> meaningless: "sum of prices" is not revenue
average order value, discount percentage, margin %  -> never add or average them blindly
```

The average trap, with small numbers:

```text
January:   2 orders, average order value 100   (total 200)
February:  8 orders, average order value  50   (total 400)

Average of the two averages:  (100 + 50) / 2  = 75     <- wrong
True average:                 (200 + 400) / 10 = 60    <- right
```

Rule of thumb: store the additive parts (amount, count) and compute ratios or
averages **at the end**, from the totals.

**Semi-additive** — adds up across some dimensions but not across time. The
classic example is a balance: stock on hand, or money in a bank account. Our
shop does not track stock, but imagine "laptops in warehouse" on Monday (10)
and Tuesday (8). You can add the warehouses together for one day, but
"10 + 8 = 18 laptops" over two days is nonsense. You will meet these later in
other projects; `fact_sales` has none.

---

## 8. Small SQL example (runs today on `raw`)

This query builds "fact-like" rows for Alice's order directly from the raw
tables, so you can see facts and dimension attributes side by side:

```sql
SELECT
    oi.order_id,
    p.product_name,
    p.category,
    c.city,
    oi.quantity,
    oi.unit_price,
    oi.discount_amount,
    oi.quantity * oi.unit_price - oi.discount_amount AS net_amount
FROM raw.order_items AS oi
JOIN raw.orders      AS o ON o.order_id    = oi.order_id
JOIN raw.products    AS p ON p.product_id  = oi.product_id
JOIN raw.customers   AS c ON c.customer_id = o.customer_id
WHERE o.customer_id = 1
  AND o.ordered_at::DATE = DATE '2026-01-15';
```

Try it:

```bash
make query SQL="SELECT oi.order_id, p.product_name, p.category, c.city, oi.quantity, oi.unit_price, oi.discount_amount, oi.quantity * oi.unit_price - oi.discount_amount AS net_amount FROM raw.order_items AS oi JOIN raw.orders AS o ON o.order_id = oi.order_id JOIN raw.products AS p ON p.product_id = oi.product_id JOIN raw.customers AS c ON c.customer_id = o.customer_id WHERE o.customer_id = 1 AND o.ordered_at::DATE = DATE '2026-01-15'"
```

You should see two rows (laptop 1263.85, mice 50.00).

### Line by line

- `FROM raw.order_items AS oi` — we start from the table whose grain matches
  "one product line in one order". Starting anywhere else would change the
  number of rows.
- The three `JOIN`s add the *when/who* (orders), the *what* (products) and
  the *where* (customers). Each line has exactly one order, one product and
  one customer, so the joins add columns without adding rows.
- `p.product_name, p.category, c.city` — **dimension attributes** (group/filter).
- `oi.quantity, oi.discount_amount, net_amount` — **measures** (sum).
- `oi.unit_price` — a number, but non-additive (see section 7).
- `oi.quantity * oi.unit_price - oi.discount_amount` — the line net amount.
  `discount_amount` is for the **whole line**, not per unit, so it is
  subtracted once, after multiplying.
- `WHERE ... ordered_at::DATE = DATE '2026-01-15'` — `::DATE` cuts the time
  off the timestamp so we can compare to a calendar day.

### Why `unit_price` and not `products.list_price`?

`products.list_price` is today's price. `order_items.unit_price` is the price
**at the moment of sale**. Some products got more expensive on 2026-01-01:

```bash
make query SQL="SELECT p.product_name, p.list_price AS current_list_price, oi.unit_price AS price_paid, year(o.ordered_at) AS order_year, count(*) AS order_lines FROM raw.order_items AS oi JOIN raw.orders AS o ON o.order_id = oi.order_id JOIN raw.products AS p ON p.product_id = oi.product_id WHERE p.product_name = 'Laptop 14-inch' GROUP BY ALL ORDER BY order_year"
```

Laptops sold in 2025 cost 1099.00; the catalog now says 1263.85. Revenue
computed from `list_price` would rewrite history. The price paid belongs to
the **event**; the current price is a **description** of the product.

---

## 9. Fan-out: the most common way to double-count

`orders.order_total` is a header copy of the sum of the line amounts. It lives
at the **order** grain. Watch what happens if you join it to the **line** grain:

```bash
make query SQL="SELECT o.order_id, SUM(o.order_total) AS wrong_total, SUM(oi.quantity * oi.unit_price - oi.discount_amount) AS right_total FROM raw.orders AS o JOIN raw.order_items AS oi ON oi.order_id = o.order_id WHERE o.order_id = 3226 GROUP BY o.order_id"
```

```text
order_id   wrong_total   right_total
3226       2627.70       1313.85
```

The join copied the order header onto both lines, so `order_total` was counted
twice. This is called **fan-out**: a join to a "many" side multiplies the rows
of the "one" side. Payments do the same thing: order 1001 has 2 lines and 2
payment events (one failed, one succeeded), so joining all three tables gives
4 rows, and summing `payments.amount` gives four times the real total.

Keep this in mind when you decide what goes on `fact_sales`.

---

## 10. A proposal to critique (not a final design)

Here is a **candidate** that you will challenge in Phase 3. It comes from the
project brief and is intentionally not settled.

```text
fact_sales (candidate)

sales_key          ?   do we need our own row id?
order_id           ?   a reference back to the source
order_item_id      ?   which source row produced this one
date_key           →   dim_date
customer_key       →   dim_customer
product_key        →   dim_product
quantity           measure
unit_price         ?   measure? non-additive...
gross_amount       ?   quantity * unit_price
discount_amount    measure
net_amount         measure
```

Open questions for you to answer in Phase 3:

```text
1. Which order statuses count as a "sale"? completed only? shipped? pending?
   (Cancelled orders still have rows in order_items.)
2. Is orders.order_total a measure for THIS table? What grain does it live at?
3. Should unit_price be stored if we should never SUM it?
4. Are gross_amount and net_amount worth storing, or should we compute them in every query?
5. Should the dimension keys be the source ids (customer_id) or new numbers
   created by the warehouse (customer_key)? The next lesson covers this.
6. Do payments belong in fact_sales at all? What is the grain of payments?
```

---

## 11. Common beginner mistakes

- **Not defining grain first.** Without "one row = ...", you cannot tell
  whether a number is safe to sum. Grain = what one row represents; the
  column(s) unique per row are how you check it.
- **Mixing grains in one fact table.** Putting `order_total` (order grain) on
  a line-grain table invites double-counting.
- **Double-counting after joins.** Any join from lines to payments or to
  order headers can fan out.
- **Confusing facts and dimensions.** `category` is not a fact just because it
  appears on every sale; it describes the product.
- **Summing non-additive numbers.** `SUM(unit_price)` and averages of averages.
- **Using the current price for historical revenue.** `list_price` ≠ price paid.
- **Putting every column everywhere.** A fact row does not need `email` or
  `brand`; it needs a key that leads to them.

---

## 12. Small exercise

Without writing SQL, sort every column of the five raw tables
(`customers`, `products`, `orders`, `order_items`, `payments`)
into one of four buckets:

```text
A) measure (I would SUM it)
B) dimension attribute (I would GROUP BY / filter by it)
C) key / identifier (it links rows together)
D) not useful for sales analysis
```

Then answer:

1. `customers.created_at` — which bucket, and which business question from the
   brief would use it?
2. `discount_amount` is for the whole line. If a line has quantity 3 and
   discount 6.00, what is the discount *per unit*, and why might storing a
   per-unit discount be a bad idea?
3. Is "number of orders" additive across days? Across products? (Careful: one
   order can contain several products.)

<details><summary>Hint</summary>

For 1, look at the question "How many customers are new each month?".
For 3, count Alice's order once per product it contains and see what happens
to "number of orders by category" when you add the categories back together.
`COUNT(DISTINCT order_id)` exists for a reason.

</details>

---

## 13. Before continuing, I should be able to explain:

```text
□ What a fact is, using Alice's order as the example
□ What a dimension is, and name the three we are proposing
□ The difference between a measure and a dimension attribute
□ Why quantity and net_amount are additive but unit_price is not
□ Why an average of averages is usually wrong
□ What semi-additive means (one example)
□ Why list_price must not be used for historical revenue
□ How joining order_total or payments to order lines double-counts
□ At least three open questions about the candidate fact_sales
```

---

**Next →** [Phase 3 · Lesson 2 — Star schema](phase-3-lesson-2-star-schema.md)
