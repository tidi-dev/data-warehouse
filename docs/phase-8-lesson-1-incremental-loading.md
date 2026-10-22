# Phase 8 · Lesson 1 — Incremental Loading: Only Process What Changed

> **Preview — Phase 8 · Lesson 1 of 1.** Read this to understand the idea. Do not build anything from this page yet; we implement it together in Phase 8.

---

## 1. What problem are we solving?

Imagine our warehouse is a few years older and bigger:

```text
Warehouse already contains:   100,000 order rows
New source data since
yesterday's load:                 500 rows
```

> Should we rebuild everything?

Rebuilding means re-reading and re-writing 100,000 rows to absorb 500
new ones — 99.5% of the work produces exactly what we already had. With
our small DuckDB file that takes seconds, so it does not matter. With a
billion rows in a cloud warehouse it costs hours and real money.

So the question becomes: *can we process only what is new or changed —
without ever getting the numbers wrong?* The second half of that
sentence is the hard part.

---

## 2. Plain-English explanation

There are two ways to keep the warehouse up to date:

- **Full refresh:** throw the table away and rebuild it from all source
  data, every time. Slow on big data, but almost impossible to get wrong.
- **Incremental load:** remember how far you got last time, fetch only
  rows that are new or changed since then, and merge them in. Fast, but
  there are several ways to get it subtly wrong.

**Our project today uses a full refresh.** `make load` runs
`scripts/load_data.py`, which does `CREATE OR REPLACE TABLE raw.orders AS
SELECT ... FROM read_csv(...)` for every table inside one transaction.
That is a deliberate choice: learn full refresh first, because it is the
safe baseline that incremental loading has to match.

---

## 3. Real-world analogy

Your email inbox. When you open your mail app it does not re-download
every email since 2015. It remembers "I last synced at 09:14" and asks
the server "anything new since 09:14?". That remembered time is a
**watermark**.

But email also gets *changed*: you mark a message as read on your laptop,
and your phone has to find out. So "new since 09:14" is not enough — it
must be "new **or changed** since 09:14".

---

## 4. E-commerce example: the order that changed after we loaded it

Our orders do not stay still. Look at the statuses in the generated data:

```bash
make query SQL="SELECT order_status, count(*) AS orders, max(ordered_at) AS latest FROM raw.orders GROUP BY order_status ORDER BY order_status"
```

You will find a few dozen recent orders that are still `pending` or
`shipped`. In real life they will become `completed` (or `cancelled`) in
the next days — the row's `updated_at` moves forward, but its `ordered_at`
stays the same.

For example, order 5401 is `shipped` in our generated data. Imagine the
source system a few days later:

```text
What we loaded on 2026-09-30        Source on 2026-10-02 (imagined)

order_id  status   updated_at       order_id  status     updated_at
5401      shipped  09-28 01:51      5401      completed  10-02 09:00   <-- changed!
```

If our incremental logic only looked for **new orders** (`ordered_at`
after the last load), order 5401 would stay `shipped` in the warehouse
forever. Revenue that counts only completed orders would be too low, and
nobody would notice.

This is called a **late-arriving update**: a change to a row we have
already loaded. The fix is to use a column that moves whenever the row
changes — in our source that is `updated_at`.

---

## 5. Diagram

```text
                       watermark = latest updated_at we have already loaded
                                    │
source rows:  ─────────────────────┼──────────────────────►  time (updated_at)
              old, already loaded   │   new OR changed rows
                                    │   (fetch only these)
                                    ▼
                         ┌─────────────────────┐
                         │ merge into warehouse│  by key: order_id
                         │  - new key  -> insert│
                         │  - known key-> update│
                         └─────────────────────┘
                                    │
                                    ▼
                  save new watermark = max(updated_at) just loaded
```

---

## 6. Official terminology

| Term | Plain meaning |
|---|---|
| **Full refresh** | Rebuild the whole table from scratch every run. |
| **Incremental load** | Process only rows that are new or changed since the last run. |
| **Watermark** | The "how far did I get?" marker, usually the max `updated_at` already loaded. |
| **Change column** (`updated_at`) | A column the source updates every time a row changes. Incremental loading depends on it being trustworthy. |
| **Late-arriving update** | A change to a row that was already loaded (order shipped → completed). |
| **Idempotency** | Running the same load twice with the same input gives the same result as running it once. |
| **Upsert** | "Update if the key exists, insert if it doesn't." |
| **MERGE** | The SQL statement that does an upsert (and optionally deletes) in one go. |
| **Delete + insert** | Delete every row whose key appears in the new batch, then insert the batch. Simple and idempotent. |

---

## 7. Idempotency: the property that saves you

> Running the same pipeline twice with the same input should not corrupt
> or duplicate the warehouse.

Pipelines get re-run all the time: a job times out and the scheduler
retries it, someone runs it manually "just to be sure", a backfill
replays last week.

```text
Run #1   input: 100 sales      warehouse: 100 sales

Run #2   same input again

BAD   (append blindly)         warehouse: 200 sales   revenue doubled
GOOD  (replace / merge by key) warehouse: 100 sales   revenue unchanged
```

The BAD version is a plain `INSERT INTO ... SELECT ...` with no check for
rows that are already there. The dashboard does not crash; it just shows
twice the revenue. That is the scariest kind of bug: silent.

Our current `make load` is idempotent **because** it is a full refresh:
`CREATE OR REPLACE TABLE` throws away the old table, so loading the same
CSVs twice gives exactly the same row counts. You can try it: run
`make load` twice and compare `SELECT count(*) FROM raw.orders` after each.
(The bookkeeping column `_loaded_at` does change — it records *when* the
load ran — but the business data and the row counts are identical.)
`make test` checks this for you on every run, in
`tests/test_load_data.py::test_loading_twice_does_not_duplicate_rows`.

---

## 8. Small SQL examples

### 8a. Finding changed rows with a watermark (runs today)

Pretend our last load saw everything up to `2026-09-25 00:00:00`:

```bash
make query SQL="
SELECT order_status, count(*) AS changed_orders
FROM raw.orders
WHERE updated_at > TIMESTAMP '2026-09-25 00:00:00'
GROUP BY order_status
ORDER BY order_status
"
```

Then compare with orders **placed** before the watermark but **changed**
after it — the late-arriving updates:

```bash
make query SQL="
SELECT count(*) AS late_updates
FROM raw.orders
WHERE ordered_at <  TIMESTAMP '2026-09-25 00:00:00'
  AND updated_at >  TIMESTAMP '2026-09-25 00:00:00'
"
```

A filter on `ordered_at` would miss every one of those.

### 8b. Merging the changes in (concept only — do not run)

These statements write data. `make query` opens the warehouse read-only,
and the target table `stg_orders` is **future — it does not exist yet**.
Read them; we write the real version together in Phase 8.

```sql
-- Option 1: delete + insert
BEGIN TRANSACTION;
DELETE FROM stg_orders
WHERE order_id IN (SELECT order_id FROM changed_orders);
INSERT INTO stg_orders
SELECT order_id, customer_id, order_status, order_total, ordered_at, updated_at
FROM changed_orders;
COMMIT;

-- Option 2: MERGE (upsert by key)
MERGE INTO stg_orders AS target
USING changed_orders AS source
    ON target.order_id = source.order_id
WHEN MATCHED THEN
    UPDATE SET order_status = source.order_status,
               order_total  = source.order_total,
               updated_at   = source.updated_at
WHEN NOT MATCHED THEN
    INSERT (order_id, customer_id, order_status, order_total, ordered_at, updated_at)
    VALUES (source.order_id, source.customer_id, source.order_status,
            source.order_total, source.ordered_at, source.updated_at);
```

---

## 9. Line by line

**8a:**

- `WHERE updated_at > TIMESTAMP '2026-09-25 00:00:00'` — "everything that
  is new or changed since my watermark". Brand-new orders qualify too,
  because a new row's `updated_at` is at least its `ordered_at`.
- `GROUP BY order_status` — just to show *what kind* of rows changed:
  you will see `completed` and `shipped` rows among them.
- The second query is the proof that `ordered_at` is the wrong column
  for finding changes.

**8b, Option 1 (delete + insert):**

- `BEGIN TRANSACTION ... COMMIT` — both steps succeed together or not at
  all. Without it, a crash between the two leaves orders deleted but not
  re-inserted.
- `DELETE ... WHERE order_id IN (...)` — remove any old version of the
  changed orders.
- `INSERT ... FROM changed_orders` — add the fresh versions. Running this
  twice deletes and re-inserts the same rows: idempotent.

**8b, Option 2 (MERGE):**

- `ON target.order_id = source.order_id` — the **key** that decides
  "same order or new order?". Choosing it correctly is everything; it
  must match the table's grain (one row per `order_id`).
- `WHEN MATCHED THEN UPDATE SET ...` — order 5401 exists, so update its
  status from `shipped` to `completed`.
- `WHEN NOT MATCHED THEN INSERT ...` — a brand-new order, insert it.
- Run it twice with the same `changed_orders`: the second run updates
  rows to the values they already have. Still idempotent.

After a successful merge, the pipeline saves the new watermark (the max
`updated_at` it just loaded) so the next run starts from there.

---

## 10. Common beginner mistakes

- **Going incremental before full refresh is understood and correct.**
  Incremental is an optimization. Its result must equal what a full
  refresh would produce — so you need a correct full refresh to compare
  against.
- **Appending instead of merging.** `INSERT` without a key check is the
  Run #2 = 200 sales bug.
- **Using `ordered_at` / `created_at` as the watermark.** You catch new
  rows and miss every late-arriving update.
- **Saving the watermark before the data is safely written.** If the load
  then fails, the next run skips those rows forever.
- **Using `>=` vs `>` carelessly.** `>` can skip rows that share the exact
  watermark timestamp; `>=` re-reads them. With an idempotent merge,
  re-reading is harmless — another reason idempotency matters.
- **Forgetting deletes.** If the source hard-deletes a row, no
  `updated_at` ever tells you. Our source never deletes, but real ones do.
- **Trusting `updated_at` blindly.** If some code path in the app forgets
  to bump it, the change is invisible to the warehouse.
- **Merging on the wrong key.** Merging `order_items` changes on
  `order_id` would collapse several product lines into one.

---

## 11. Small exercise

1. Without running anything, explain why our `make load` cannot produce
   duplicates even if you run it ten times in a row.
2. Suppose a careless loader *appended* the CSV rows with a plain
   `INSERT INTO raw.orders ...` instead of `CREATE OR REPLACE TABLE`.
   What would `SELECT count(*) FROM raw.orders` show after three runs?
   What would monthly revenue show?
3. Which key would you merge on for each table: `orders`, `order_items`,
   `payments`? Which tables even have an `updated_at`?
4. `order_items` and `payments` have **no** `updated_at`. How could an
   incremental load notice that something about them changed?

<details><summary>Hint for 2</summary>

Each run appends the whole file again. Think "Run #1 / Run #2 / Run #3".

</details>

<details><summary>Hint for 3</summary>

The merge key must identify exactly one row — it is the table's grain.
Use your "one row = ..." sentence for `payments` from Phase 2, inspect the
columns with `make query SQL="DESCRIBE raw.payments"`, and check uniqueness
with `count(*)` vs `count(DISTINCT ...)`.

</details>

<details><summary>Hint for 4</summary>

Think about the parent row. When an order's lines change, does something
on the order header change too? And payments are *events*: are old ones
ever edited, or are new ones just added?

</details>

---

## 12. Before continuing, I should be able to explain:

```text
□ What is the difference between a full refresh and an incremental load?
□ Why is our current make load a full refresh, and why is it idempotent?
□ What is a watermark, and which column would I use for raw.orders?
□ What is a late-arriving update? Give the shipped -> completed example.
□ Why does filtering on ordered_at miss changes?
□ What is idempotency, and what goes wrong in the "Run #2 = 200 sales" case?
□ How do delete + insert and MERGE each avoid duplicates?
□ Why should the watermark be saved only after the data is written?
□ Why do incremental loads exist, and why does idempotency matter?   <── Phase 8 goal
```

---

This is the last lesson for now. Phase 9 (platform evolution) is a discussion with the tutor — no new lesson file.
