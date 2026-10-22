# Phase 1 · Lesson 3 — OLTP vs OLAP: Running the Business vs Understanding It

> **Phase 1 · Lesson 3 of 3 — the last lesson of Phase 1.** After this
> lesson you can explain why companies separate operational and analytical
> workloads.

---

## 1. What problem are we solving?

The same company data gets used in two very different ways. If we don't
notice the difference, we end up with one database that is bad at both
jobs.

---

## 2. Start with what the shop *does*

Here are things that happen thousands of times a day on our shop's website:

```text
Create an order               INSERT one row in orders, a few in order_items
Update a customer's address   UPDATE one row in customers
Find order #1234              SELECT one row by its id
Process a payment             INSERT one row in payments
Change product stock          UPDATE one row in products
```

What do these have in common?

- Each one touches **very few rows** (usually 1–5).
- Each one must be **fast** (milliseconds — a customer is waiting).
- Many happen **at the same time** (hundreds of shoppers).
- They **change** data (insert / update / delete).
- They must be **safe**: an order must never be half-saved, a payment
  never recorded twice.

---

## 3. Now what the CEO *asks*

```text
Revenue by month?
Top categories this year?
Average order value?
Revenue by region?
How many new customers each month?
```

What do these have in common?

- Each one reads **lots of rows** (every order ever placed).
- It reads only **a few columns** (amount, date, category) out of many.
- It only **reads**; nothing is changed.
- Nobody minds waiting a second or two.
- It is about **groups and trends**, not about one specific order.

---

## 4. The mental model

```text
     OLTP                                OLAP
       =                                   =
  RUN the business                 UNDERSTAND the business

  "Save Alice's order."            "How much did customers in the
  "Find order #1234."               South spend per month in 2025?"

  few rows, many users,            many rows, few users,
  lots of small writes             big reads, few writes
```

---

## 5. Real-world analogy

A **cash register** vs a **year-end report**.

- The cash register (OLTP) must ring up each customer in seconds, all day,
  without mistakes. It doesn't care about last year.
- The year-end report (OLAP) reads every receipt of the year, groups them
  and adds them up. It's fine if it takes a while, but you would never run
  it *on the register* while customers queue.

---

## 6. Official terminology

| Term | Stands for | Plain English |
|---|---|---|
| **OLTP** | OnLine **Transaction** Processing | Systems that *run* the business: many tiny, fast reads and writes. |
| **OLAP** | OnLine **Analytical** Processing | Systems that *analyze* the business: big read-only queries that summarize lots of rows. |
| **Transaction** | — | A group of changes that succeed or fail together ("save the order AND its items, or nothing"). |
| **Workload** | — | The kind of queries a system mostly receives. |

Typical OLTP databases: PostgreSQL, MySQL, SQL Server, Oracle.
Typical OLAP engines: DuckDB, ClickHouse, BigQuery, Snowflake, Redshift.

---

## 7. Why are they built differently? (rows vs columns)

Picture `order_items` with 8 million rows. The OLAP question "total units
sold" only needs the `quantity` column.

**Row storage** (typical OLTP database) keeps each *row* together on disk:

```text
[1001, 53, 2, 26.00, 0.00] [1001, 12, 1, 1799.00, 0.00] [1002, 7, 1, 29.00, 0.00] ...
  ▲ great for "give me order item 1"  — one read gets the whole row
  ▼ bad for "sum all quantities"      — must read every column of every row
```

**Column storage** (typical OLAP engine, including DuckDB) keeps each
*column* together:

```text
order_id:   [1001, 1001, 1002, ...]
product_id: [53,   12,   7,    ...]
quantity:   [2,    1,    1,    ...]   ◄── "sum all quantities" reads only this
unit_price: [26.00, 1799.00, 29.00, ...]
```

Column storage also compresses well (a column of similar values shrinks a
lot) and lets the engine process thousands of values at once. That's why
analytical engines are fast at `SUM ... GROUP BY` over millions of rows and
comparatively slow at changing single rows.

You don't need to remember the internals. Remember the trade-off:

```text
Row storage     → fast at finding/changing ONE row        → OLTP
Column storage  → fast at summarizing MANY rows, few cols → OLAP
```

---

## 8. Why do companies separate the two?

```text
                   ┌──────────────────────┐
   shoppers ─────► │  OLTP database       │   PostgreSQL, MySQL, ...
                   │  (website)           │
                   └──────────┬───────────┘
                              │ copy data out (e.g. every night)
                              ▼
                   ┌──────────────────────┐
   analysts ─────► │  OLAP warehouse      │   DuckDB (this project),
                   │  (understanding)     │   BigQuery, Snowflake, ...
                   └──────────────────────┘
```

1. **Protection.** A heavy report can't slow down checkout if it runs on a
   different system.
2. **Right tool for the job.** Each engine is optimized for its workload
   (rows vs columns, see above).
3. **History.** The website overwrites values (Alice's new address replaces
   the old one). The warehouse can keep history on purpose.
4. **Shape.** The warehouse can be reorganized around business questions
   instead of around saving orders correctly.
5. **One version of the truth.** Business rules ("revenue excludes cancelled
   orders") are written once in the warehouse, not re-invented by every
   analyst.

---

## 9. Our project: which piece is which?

```text
OLTP side (simulated)                    OLAP side (real)

data/source/customers.csv   ──┐
data/source/products.csv    ──┤  make load   ┌──────────────────────────┐
data/source/orders.csv      ──┼────────────► │ warehouse/warehouse.duckdb│
data/source/order_items.csv ──┤              │ schema: raw               │
data/source/payments.csv    ──┘              └──────────────────────────┘
```

We don't run a real PostgreSQL shop database — that would add
infrastructure without teaching anything about warehousing. The CSV files
play the role of "an export from the shop's database".

**Why DuckDB for the warehouse?** It is an OLAP engine (column storage) that
runs *inside* our Python process and keeps the whole warehouse in one file.
No server to operate, so we can focus on warehouse concepts. And because
it's one file on your disk, TablePlus can open it directly.

---

## 10. Small SQL example — feel the difference

Your warehouse is already loaded (Lesson 2), so you can run these now.

An **OLTP-style** query — find one order:

```bash
make query SQL="SELECT * FROM raw.orders WHERE order_id = 1234"
```

An **OLAP-style** query — summarize all orders:

```bash
make query SQL="SELECT date_trunc('month', ordered_at) AS month, count(*) AS orders FROM raw.orders GROUP BY month ORDER BY month"
```

### Line by line (the second query)

| Part | Meaning |
|---|---|
| `date_trunc('month', ordered_at)` | Turn `2025-03-17 14:02:11` into `2025-03-01` — "which month?" |
| `AS month` | Name that result column `month` |
| `count(*)` | Count the rows in each group |
| `FROM raw.orders` | Read the orders table in the `raw` schema of the warehouse |
| `GROUP BY month` | One output row per month |
| `ORDER BY month` | Oldest month first |

The first query touched **one** row. The second touched **every** order and
produced ~21 rows. Same data, completely different workload.

---

## 11. Common beginner mistakes

- **Thinking OLTP and OLAP are products.** They're *workload types*. A
  PostgreSQL database *can* run analytical queries; it's just not built for
  them at scale.
- **Treating DuckDB like PostgreSQL.** DuckDB is not a server you connect to
  over a port. It's a library + a file. Only one process should write to the
  file at a time — that's why you disconnect TablePlus before `make load`
  (Lesson 2).
- **Using the operational schema directly for every analytical question.**
  It works at first, then every analyst re-implements "what counts as
  revenue" slightly differently.
- **Thinking the warehouse replaces the operational database.** It doesn't.
  The shop still needs its OLTP database to take orders. The warehouse is
  an additional, downstream system.

---

## 12. Small exercise

Classify each as **OLTP** or **OLAP**, and say *why* in a few words:

```text
a) A customer changes their email address.
b) Marketing wants the number of new customers per month in 2025.
c) The website shows "Your order #2042 has shipped".
d) Finance compares revenue by category this quarter vs last quarter.
e) The checkout page checks that a product is still active.
f) A dashboard shows the top 10 products by revenue for the year.
```

<details><summary>Hint</summary>

Ask two questions for each: *How many rows does it touch?* and *Does it
change data or summarize data?*

</details>

---

## 13. Before continuing, I should be able to explain:

```text
□ What is OLTP? Give one example from our shop.
□ What is OLAP? Give one example from our shop.
□ Why is column storage good for analytical queries?
□ Name three reasons to separate operational and analytical workloads.
□ In our project, what plays the role of the OLTP system, and what is the OLAP warehouse?
□ Why would a company use a warehouse instead of running every analytical
  query directly against its application database?   ◄── Phase 1 goal
```

---

**Next →** [Phase 2 · Lesson 1 — Understanding the source data](phase-2-lesson-1-understanding-source-data.md)
