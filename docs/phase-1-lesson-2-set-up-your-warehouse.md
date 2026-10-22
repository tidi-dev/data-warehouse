# Phase 1 · Lesson 2 — Set Up Your Warehouse

> **Phase 1 · Lesson 2 of 3.** Hands on: build the tools, create the shop's
> data and load it into your warehouse. Everything you need is on this page.

---

## 1. What problem are we solving?

The last lesson drew the map: operational data → extract → raw copy in the
warehouse → … → business answers. Before going further, you need the first
two boxes **on your own computer**, so that every later lesson can show you
real rows instead of pictures.

```text
  Operational data   ──►  Extract + Load  ──►  Raw data in the warehouse
  data/source/*.csv       make load            warehouse/warehouse.duckdb, schema raw
        ▲
        └── make generate-data
```

---

## 2. What you need on your computer

```text
Git
Docker (with Docker Compose v2 — check with: docker compose version)

Optional:
TablePlus   (to browse the warehouse and practice SQL)
```

You do **not** need Python, DuckDB, dbt or pytest on your computer. They
live inside a Docker **image** (a frozen toolbox). Every `make ...` command
starts a throwaway **container** from that image, runs one command in it,
and deletes the container again. The project folder is shared with the
container, so files it writes (the CSVs, the warehouse) appear in your
project folder and stay there.

---

## 3. Step by step

Run these from the project folder, in this order.

### Step 1 — build the toolbox (first time: a few minutes)

```bash
make build
```

### Step 2 — create the shop's data

```bash
make generate-data
```

This writes five CSV files to `data/source/`. They play the role of an
export from the shop's website database. The generator uses a fixed seed
(42), so **everyone gets exactly the same data** — the numbers in these
lessons will match yours.

### Step 3 — load it into the warehouse

```bash
make load
```

This copies the five CSVs, untouched, into `warehouse/warehouse.duckdb`,
in a schema (a folder for tables) called **`raw`**. It's a *full refresh*:
each run replaces the tables completely, so running it twice is harmless.

### Step 4 — look at what you loaded

```bash
make query
```

Without arguments it lists the tables. You should see five, all in `raw`:

```text
customers  products  orders  order_items  payments
```

Now ask a real question (read-only — `make query` can never change data):

```bash
make query SQL="SELECT count(*) FROM raw.orders"
```

You should get **4,429** orders.

### Step 5 — check the project works

```bash
make test
```

All tests should pass. They check our assumptions about the data (for
example: every order has at least one line, and loading twice doesn't
duplicate rows).

---

## 4. Optional: open the warehouse in TablePlus

`make query` is enough for the whole course. TablePlus is nicer for
browsing.

1. In TablePlus: **Create a new connection… → DuckDB**.
2. Choose the file `warehouse/warehouse.duckdb` inside this project folder.
3. Connect. TablePlus first shows the schema **`main`, which is empty** —
   that's expected. Our tables are in schema **`raw`**: switch the schema,
   or open a SQL tab and always write the `raw.` prefix:

```sql
SELECT * FROM raw.orders LIMIT 10;
```

### The one rule you must remember: one writer at a time

DuckDB is not a server — it's a single file. Only **one** program may
write to it at a time. Normally DuckDB stops a second writer with an
error, but between your Mac and the Docker container that protection does
**not** work (we tested it): both programs carry on, and the file can be
damaged.

```text
Disconnect TablePlus  →  run make load  →  reconnect TablePlus
```

`make query` and `make test` are safe at any time. If the warehouse ever
looks broken, it's disposable — rebuild it exactly:

```bash
make clean            # deletes the CSVs and the warehouse file
make generate-data
make load
```

---

## 5. All the commands, in one place

| Command | What it does | Changes the warehouse? |
|---|---|---|
| `make build` | Build the Docker image (the toolbox) | no |
| `make generate-data` | Write the shop's data to `data/source/*.csv` | no |
| `make load` | Full-refresh the CSVs into schema `raw` | **yes** — disconnect TablePlus first |
| `make query SQL="..."` | Run one SQL query, read-only | no |
| `make test` | Run the tests | no |
| `make shell` | Open a shell inside the container | — |
| `make versions` | Show tool versions | no |
| `make down` | Remove leftover containers (your files stay) | no |
| `make clean` | **Delete** the CSVs and the warehouse file | deletes it |

---

## 6. Common beginner mistakes

- **Opening TablePlus and seeing no tables.** You're looking at schema
  `main`. The tables are in `raw`.
- **Leaving TablePlus connected while running `make load`.** Disconnect
  first, every time.
- **Expecting `docker compose up` to start a database.** There is no
  database server. Use the `make` commands.
- **Rebuilding the image after every change.** Only `make build` again if
  `requirements.txt` or the `Dockerfile` changes.

---

## 7. Small exercise

Run each query and write down the answer. You'll need these numbers in
Phase 2.

```bash
make query SQL="SELECT count(*) FROM raw.customers"
make query SQL="SELECT count(*) FROM raw.products"
make query SQL="SELECT count(*) FROM raw.order_items"
make query SQL="SELECT count(*) FROM raw.payments"
make query SQL="SELECT * FROM raw.orders LIMIT 5"
```

Looking at the five orders: which column tells you *who* bought, and which
tells you *when*?

---

## 8. Before continuing, I should be able to:

```text
□ Run make build, make generate-data, make load and make test without errors.
□ Say where the source data lives (data/source/*.csv) and where the warehouse lives
  (warehouse/warehouse.duckdb, schema raw).
□ Run a read-only query with make query.
□ Explain why TablePlus must be disconnected before make load.
```

> Want to know more about how Docker is set up here? That's optional:
> [reference/docker.md](reference/docker.md).

---

**Next →** [Phase 1 · Lesson 3 — OLTP vs OLAP](phase-1-lesson-3-oltp-vs-olap.md)
