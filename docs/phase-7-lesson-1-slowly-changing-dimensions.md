# Phase 7 · Lesson 1 — Slowly Changing Dimensions: When Alice Moves House

> **Preview — Phase 7 · Lesson 1 of 1.** Read this to understand the idea. Do not build anything from this page yet; we implement it together in Phase 7.

Quick recap from Phase 3: a **fact table** records what happened (one row
per product line sold, with the amounts); **dimension tables** describe it
(which customer, which product, which date); in a **star schema** each
dimension joins directly to the fact by a key. Everything here is a small
twist on a normal dimension.

---

## 1. What problem are we solving?

Meet Alice Nguyen, customer #1 in our shop.

```text
2026-01-15   Alice lives in Ho Chi Minh City (South).
             She buys a Laptop 14-inch x 1 and a Wireless Mouse x 2.

2026-06      Alice moves to Da Nang (Central).
             She updates her profile in the app.

2026-12      The CEO asks: "How much revenue did each region
             make in January 2026?"
```

Here is the question this whole lesson is about:

> When we analyze Alice's January purchase in December, which city and
> region should that sale belong to — Ho Chi Minh City / South, or
> Da Nang / Central?

Take a moment and answer it for yourself before reading on. There is no
universally right answer. That is exactly why this topic exists.

---

## 2. Plain-English explanation

Customer details change slowly over time: people move, get married,
upgrade from `standard` to `premium`. Product details change too: a
product moves to another category, its price goes up.

When a detail changes, the warehouse has two basic choices:

- **Overwrite it.** Keep only the latest value. Simple, but the past
  now looks as if Alice always lived in Da Nang.
- **Keep both versions.** Remember "Alice in HCMC from July 2024 to
  June 2026" *and* "Alice in Da Nang from June 2026 onwards". More work,
  but history stays true.

Our source system already made its choice: it **overwrites**. Look at
`raw.customers` — it only has the *current* city. About 15% of customers
have `updated_at > created_at`, which tells us *something* changed, but
the old values are gone forever. If we want history, the warehouse must
start remembering it from now on — the source will not do it for us.

---

## 3. Real-world analogy

Think of your phone's contact list versus a printed address book.

- Your phone contact for a friend gets **edited** when they move. The
  old address disappears. Handy for sending a parcel today.
- A diary in which you wrote "visited Minh at his flat in Hue" in 2024
  still says Hue, even though Minh lives in Ha Noi now. That diary
  **preserved history**. Handy for answering "where was I in 2024?"

Both are useful. They answer different questions.

---

## 4. E-commerce example

Imagine the January 2026 revenue-by-region report, run twice.

```text
Report run in February 2026 (before Alice moved)
    South     ...  includes Alice's 1,313.85
    Central   ...

Report run in December 2026, warehouse OVERWRITES customer details
    South     ...  1,313.85 LOWER than in February
    Central   ...  1,313.85 HIGHER than in February
```

The January sales did not change. Nobody bought or returned anything.
Yet the January report changed, because Alice's *current* region was
used. A finance team that compares the two printouts will be very
confused.

Now the opposite case: marketing wants to send a Da Nang store-opening
email to "all customers in Central". For that question they want
Alice's **current** city. Old addresses are useless there.

---

## 5. Diagram

```text
SCD Type 1 (overwrite)                 SCD Type 2 (add a new version)

dim_customer                           dim_customer
customer_id  city                      customer_key customer_id city             valid_from  valid_to    is_current
1            Da Nang   <- was HCMC     1            1           Ho Chi Minh City 2024-07-03  2026-06-10  false
                                       2            1           Da Nang          2026-06-10  9999-12-31  true

fact_sales                             fact_sales
order 3226 ──► customer_id 1           order 3226 ──► customer_key 1  (HCMC, the version valid in January)
          (Da Nang today)              later order ──► customer_key 2 (Da Nang)
```

`dim_customer` and `fact_sales` are **future** tables — they do not exist
yet. Only the `raw` schema exists today.

---

## 6. Official terminology

| Term | What it means here |
|---|---|
| **Slowly Changing Dimension (SCD)** | A dimension whose attributes (city, segment, category) change occasionally, and the rule we pick for handling that. |
| **SCD Type 1** | Overwrite the old value. No history. The past is re-described with today's values. |
| **SCD Type 2** | Insert a new row (a *version*) for each change. History is preserved. |
| **Surrogate key** (`customer_key`) | A warehouse-made id for *one version* of a customer. Alice has one `customer_id` but two `customer_key`s. |
| **Natural key** (`customer_id`) | The id from the source system. Same for every version of Alice. |
| `valid_from` / `valid_to` | The time window in which this version was true. |
| `is_current` | A convenience flag: `true` on the newest version only. |

There are other "types" (0, 3, 4, 6). You do not need them now. Types 1
and 2 cover the vast majority of real projects.

### The trade-off, before any implementation

| | Type 1 (overwrite) | Type 2 (versions) |
|---|---|---|
| Rows per customer | always 1 | 1 + number of changes |
| Past reports | can change when someone moves | stay stable |
| "Where does the customer live *now*?" | trivial | filter `is_current = true` |
| "Where did they live *when they bought*?" | impossible | natural |
| Join from fact | on `customer_id` | on `customer_key` (or a date-range join) |
| Effort to build and test | low | noticeably higher |

A common pattern: Type 2 for the few attributes that matter for history
(city, region, segment), Type 1 for things like a typo fix in an email
address. You choose **per attribute**, based on the business questions.

---

## 7. Small SQL example

This query uses only inline data (no tables), so you *can* run it today
with `make query` without breaking anything. It pretends a Type 2
customer dimension exists and shows how a sale finds "the version of
Alice that was true at the moment she bought". Order 9001 is invented;
order 3226 is Alice's real January order in our generated data.

```bash
make query SQL="
WITH dim_customer_history AS (
    SELECT * FROM (VALUES
        (1, 1, 'Ho Chi Minh City', 'South',   TIMESTAMP '2024-07-03 10:15:00', TIMESTAMP '2026-06-10 00:00:00', false),
        (2, 1, 'Da Nang',          'Central', TIMESTAMP '2026-06-10 00:00:00', TIMESTAMP '9999-12-31 00:00:00', true)
    ) AS t(customer_key, customer_id, city, region, valid_from, valid_to, is_current)
),
sales AS (
    SELECT * FROM (VALUES
        (3226, 1, TIMESTAMP '2026-01-15 20:30:00', 1313.85),
        (9001, 1, TIMESTAMP '2026-08-02 14:00:00',   59.00)
    ) AS t(order_id, customer_id, ordered_at, revenue)
)
SELECT s.order_id, s.ordered_at, s.revenue, d.customer_key, d.city, d.region
FROM sales AS s
JOIN dim_customer_history AS d
    ON  d.customer_id = s.customer_id
    AND s.ordered_at >= d.valid_from
    AND s.ordered_at <  d.valid_to
ORDER BY s.ordered_at
"
```

Expected result (DuckDB draws a box around it; simplified here):

```text
order_id  ordered_at           revenue  customer_key  city              region
3226      2026-01-15 20:30:00  1313.85  1             Ho Chi Minh City  South
9001      2026-08-02 14:00:00    59.00  2             Da Nang           Central
```

---

## 8. Line by line

- `WITH dim_customer_history AS (...)` — a CTE that fakes a Type 2
  dimension with two rows: two *versions* of the same customer.
- `VALUES (1, 1, 'Ho Chi Minh City', ...)` — `customer_key = 1`,
  `customer_id = 1`. Version 1 was valid from her sign-up until the move.
- `(2, 1, 'Da Nang', ...)` — a new `customer_key` (2), the same
  `customer_id` (1). The `valid_to` of `9999-12-31` is a common
  convention for "still valid". Some teams use `NULL` instead.
- `sales AS (...)` — two sales: one before the move, one after.
- `ON d.customer_id = s.customer_id` — find all versions of this customer.
- `AND s.ordered_at >= d.valid_from AND s.ordered_at < d.valid_to` — keep
  only the version whose window contains the sale time. Note `>=` on one
  side and `<` on the other: a half-open window, so a sale at exactly
  `2026-06-10 00:00:00` matches exactly one version, never two.
- The result shows January's sale attached to HCMC / South and August's
  sale attached to Da Nang / Central. History is preserved.

**Important:** in a real warehouse we usually do this date-range lookup
**once, while loading the fact table**, and store `customer_key` directly
in `fact_sales`. After that, reports use a plain equality join
`fact_sales.customer_key = dim_customer.customer_key` — fast and simple.

---

## 9. How it might be built later

Not now. Just so you know the options exist:

- **Hand-written SQL** that compares today's `raw.customers` with the
  current versions in the dimension, closes changed versions
  (`valid_to = now`, `is_current = false`) and inserts new ones.
- **dbt snapshots** (future option — no dbt project exists yet). dbt has a
  built-in feature that does exactly this bookkeeping. It is convenient,
  but you will understand it far better after doing the logic by hand once.

Either way, Type 2 only records changes it *sees*. Our source keeps no
history, so changes that happened before the warehouse started watching
are lost for good.

---

## 10. Common beginner mistakes

- **Building SCD2 before understanding basic dimensions.** If you cannot
  yet explain the grain of `dim_customer` or why facts hold keys, Type 2
  adds confusion on top of confusion. Get a plain Type 1 dimension
  working first.
- **Making everything Type 2 "just in case".** Every tracked attribute
  multiplies rows and complexity. Track only what a business question
  needs.
- **Joining facts to a Type 2 dimension on `customer_id` only.** Alice
  has two rows, so every one of her sales is counted **twice**. This is a
  fan-out — the same trap as joining payments to order lines.
- **Forgetting `is_current` when you want today's view.** "How many
  customers live in Central?" must count current versions only.
- **Overlapping or gapped windows.** If `valid_to` of version 1 is not
  exactly `valid_from` of version 2, sales can match zero or two versions.
- **Expecting Type 2 to recover the past.** It cannot. History starts
  the day you start tracking.

---

## 11. Small exercise

No SQL needed.

1. For each question, decide whether it needs Type 1 or Type 2 behavior
   for the customer's region:
   - a) "Revenue by region for January 2026, as reported in February."
   - b) "Send a promo to every customer who currently lives in the North."
   - c) "Did customers who moved to Da Nang start buying more?"
2. Alice upgrades from `premium` to `business` in August 2026 (her city
   does not change). Write out the rows of a Type 2 `dim_customer` that
   tracks **both** city and segment. How many versions does Alice have?
3. In `raw.customers`, roughly how many customers have
   `updated_at > created_at`? What can and can't you learn from them?

<details><summary>Hint for 2</summary>

Each change to *any* tracked attribute closes the current version and
opens a new one. Count the changes, then add one for the original row.

</details>

<details><summary>Hint for 3</summary>

`make query SQL="SELECT count(*) FROM raw.customers WHERE updated_at > created_at"`.
You learn *when* the latest change happened — but not *what* changed.

</details>

---

## 12. Before continuing, I should be able to explain:

```text
□ What does "slowly changing dimension" mean, in my own words?
□ What happens to Alice's January sale in a Type 1 dimension after she moves?
□ What happens to it in a Type 2 dimension?
□ Why does Alice have one customer_id but two customer_key values in Type 2?
□ What are valid_from, valid_to and is_current for?
□ Why can joining a fact to a Type 2 dimension on customer_id double-count?
□ Why can't our warehouse recover changes that happened before it started tracking?
□ When would I deliberately choose Type 1 instead of Type 2?
□ What is the difference between replacing history and preserving history?   <── Phase 7 goal
```

---

**Next →** [Phase 8 · Lesson 1 — Incremental loading](phase-8-lesson-1-incremental-loading.md)
