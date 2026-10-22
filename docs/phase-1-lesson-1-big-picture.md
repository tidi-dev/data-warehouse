# Phase 1 · Lesson 1 — The Big Picture: Why Data Warehouses Exist

> **Phase 1 · Lesson 1 of 3.** Start here. No commands yet — just the map of where we are going.

---

## 1. What problem are we solving?

Imagine you run a small online shop. Your website has a database. Every time
someone signs up, a row is added to `customers`. Every time someone checks
out, rows are added to `orders` and `order_items`. Every time money moves, a
row is added to `payments`.

That database is great at one job: **keeping the shop running**.

Then, one Monday morning, the CEO asks:

```text
How much revenue did we make last month?
Which product categories are growing?
Which regions bring in the most money?
Who are our best customers?
```

You could write SQL against the website's database to answer these. Many
companies start exactly like that. But as the company grows, problems
appear:

```text
1. Big analytical queries slow down the website   → customers can't check out
2. The website database only keeps CURRENT values → "where did Alice live in
                                                     January?" is lost forever
3. The data is shaped for saving orders, not for  → every question needs
   answering questions                               complicated joins
4. Numbers disagree                               → marketing says revenue is X,
                                                     finance says Y
```

A **data warehouse** is the answer to all four problems: a *separate*
database whose only job is to help people **understand** the business.

---

## 2. Plain-English explanation

> A data warehouse is a copy of the company's data, reorganized so that
> questions are easy, fast and consistent to answer — kept away from the
> systems that run the business.

Three key words in that sentence:

| Word | Meaning |
|---|---|
| **copy** | We don't touch the website's database. We *extract* data out of it. |
| **reorganized** | We reshape the data around business questions (sales, customers, products, dates). |
| **separate** | Heavy analysis can never slow down checkout. |

---

## 3. Real-world analogy

Think of a busy restaurant.

- The **kitchen** is optimized for cooking: tickets come in, dishes go out,
  fast. Nobody stops the kitchen at 8 p.m. to count how many pasta dishes
  were sold this year.
- The **accountant's office** receives copies of every receipt at the end of
  the day, sorts them into folders (by month, by dish, by waiter) and
  answers questions like "which dish is most profitable?".

```text
   KITCHEN                         ACCOUNTANT'S OFFICE
   (runs the restaurant)           (understands the restaurant)

   tickets in ─► dishes out        receipts ─► sorted folders ─► reports
        │                                ▲
        └──── copies of receipts ────────┘
```

The kitchen is the **operational database**. The accountant's office is the
**data warehouse**.

---

## 4. E-commerce example: our project

Our fictional shop sells electronics, computers, books, kitchenware, sports
gear and beauty products to customers across Vietnam.

The operational database (we simulate it with CSV files) has five tables:

```text
customers ──< orders ──< order_items >── products
                 │
                 └──< payments

  ──<  means "one ... has many ..."
       (one customer has many orders, one order has many items)
```

The questions we want to answer in this course:

```text
How much revenue did we make this month?
How does revenue change month over month?
Which products generate the most revenue?
Which categories generate the most revenue?
Who are our highest-value customers?
What is average order value?
How many customers are new each month?
Which regions generate the most revenue?
Which categories are growing?
How many products are sold each month?
```

Keep this list in mind. Every design decision later in the course is judged
by one test: **does it make these questions easier and more trustworthy to
answer?**

---

## 5. Diagram: the whole journey

This is the full path data takes. We will walk it one step at a time.

```text
  Operational data      the shop's database (our CSV files)          ◄─ Phase 1-2
         │
         ▼
      Extract           copy it out without disturbing the shop
         │
         ▼
      Raw data          an untouched copy inside the warehouse        ◄─ Phase 1-2
         │                (DuckDB schema `raw`)
         ▼
      Staging           cleaned, renamed, correctly typed             ◄─ Phase 4
         │
         ▼
   Transformation       business rules applied                        ◄─ Phase 4
         │
         ▼
 Facts + Dimensions     "what happened" + "who/what/when"             ◄─ Phase 3-4
         │
         ▼
     Data marts         ready-made tables for a business area         ◄─ Phase 4
         │
         ▼
   Analytical SQL       SELECT ... GROUP BY ...                       ◄─ Phase 6
         │
         ▼
  Business answers      "Revenue grew 8% in March"
```

**Where we are right now:** the first two boxes. We generate the
operational data and copy it — untouched — into the warehouse so we can look
at it.

---

## 6. Official terminology

Only now, the names:

| Term | Plain English | In our project |
|---|---|---|
| **Operational database / source system** | The database that runs the business | The shop's website database (simulated by `data/source/*.csv`) |
| **Data warehouse** | A separate database designed for answering questions | `warehouse/warehouse.duckdb` |
| **Extract** | Copy data out of the source system | Reading the CSV files |
| **Load** | Put that copy into the warehouse | `make load` |
| **Transform** | Reshape and clean it for analysis | Later, with dbt |
| **Data mart** | The part of the warehouse for one business area (e.g. sales) | Later: `fact_sales` + its dimensions |

You will meet more terms in the next lessons. (Forgot a word? Every term is
also in the [glossary](reference/glossary.md) — optional, look things up only
when you need to.)

### Database vs data warehouse — are they different technologies?

Not necessarily. A data warehouse **is** a database. The difference is its
**purpose and shape**:

```text
                     DATABASE (operational)        DATA WAREHOUSE
Purpose              run the business              understand the business
Typical question     "show order #1234"            "revenue by month by region"
Rows touched         a few                         millions
Writes               constantly, tiny              in batches (e.g. nightly)
History              current state only            history kept on purpose
Shape                many small normalized tables  facts + dimensions
```

Our warehouse uses **DuckDB**, a database engine built specifically for the
right-hand column. Why that matters is the topic of Lesson 3 — first, in
Lesson 2, you'll set the warehouse up on your computer.

---

## 7. Small code example

Nothing to run yet — but here is the kind of SQL a warehouse exists to make
easy. Read it and notice how *business-shaped* it is:

```sql
-- Future example (these tables don't exist yet!)
SELECT
    d.year,
    d.month_name,
    p.category,
    SUM(f.net_amount) AS revenue
FROM fact_sales  AS f
JOIN dim_date    AS d ON f.date_key    = d.date_key
JOIN dim_product AS p ON f.product_key = p.product_key
GROUP BY d.year, d.month_name, p.category;
```

## 8. Line by line

| Line | What it means |
|---|---|
| `FROM fact_sales AS f` | Start from "everything that was sold" — one row per thing sold |
| `JOIN dim_date ...` | Attach calendar information (year, month name) to each sale |
| `JOIN dim_product ...` | Attach product information (category) to each sale |
| `SUM(f.net_amount)` | Add up the money |
| `GROUP BY ...` | One answer row per year + month + category |

Compare that to answering the same question against the shop's raw tables:
you'd need to know that revenue lives in `order_items` (not `orders`), that
the price is `unit_price` (not `products.list_price`), that discounts must be
subtracted, that cancelled orders must be excluded… The warehouse bakes
those decisions in **once**, so every analyst gets the same answer.

---

## 9. Common beginner mistakes

- **"A warehouse is just a bigger database."** It's a database with a
  different *purpose* and a different *shape*.
- **"Let's install Snowflake / Airflow / Kafka first."** Tools come last.
  The hard part is deciding what one row means and which numbers are
  correct. This course uses a single file (DuckDB) on purpose.
- **"We'll just query the production database."** Fine for a 5-person
  startup; painful once analysis slows checkout or history is needed.
- **"The pipeline ran, so the numbers are right."** Running is not the same
  as being correct. We'll test the data itself later (Phase 5).

---

## 10. Small exercise

Pick **three** questions from the list in section 4. For each one, write
down (in plain English, no SQL):

1. Which of the five source tables you think hold the information needed.
2. One thing that could make the answer *wrong* if you weren't careful.

<details><summary>Hint</summary>

For "Which categories generate the most revenue?": where does "category"
live? Where does the amount of money live? Are they in the same table? What
about cancelled orders?

</details>

---

## 11. Before continuing, I should be able to explain:

```text
□ In one sentence, what is a data warehouse?
□ Name two reasons a company might not run analytics on its website database.
□ What does "extract" mean? What does "load" mean?
□ Is a data warehouse a different kind of technology from a database?
□ Which step of the big-picture diagram are we working on right now?
```

---

**Next →** [Phase 1 · Lesson 2 — Set up your warehouse](phase-1-lesson-2-set-up-your-warehouse.md)
