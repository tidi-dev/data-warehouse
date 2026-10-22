# Docker — Just Enough for This Project

> This is not a Docker course. It explains only what you need to understand
> how this project runs and why your warehouse file is safe.

---

## 1. What problem are we solving?

To build the warehouse you need Python, DuckDB, dbt and pytest — in
versions that work together. Installing them on every learner's computer
leads to "works on my machine" problems.

Docker packages all those tools into one **image**. Everybody runs the same
image, so everybody gets the same tools and the same results. Your computer
only needs Git, Docker and Docker Compose.

---

## 2. The three words you need

```text
 Dockerfile ──── docker compose build ────► image ──── docker compose run ────► container
 (a recipe)                                 (a frozen         (a running copy of the image,
                                             toolbox)          deleted when the command ends)
```

| Word | Plain English | In this project |
|---|---|---|
| **Dockerfile** | A recipe: "start from Python 3.13, install these packages" | [`Dockerfile`](../../Dockerfile) |
| **Image** | The result of following the recipe: a frozen toolbox | `data-warehouse-dev` |
| **Container** | A running instance of the image, where a command executes | Created by every `make ...` command, removed afterwards |

**Docker Compose** is a small file ([`compose.yaml`](../../compose.yaml)) that
remembers *how* to run the container (which folder to mount, which user, …)
so you don't have to type long `docker run` commands.

The **Makefile** hides even the Compose commands:

```text
make test
   │  is shorthand for
   ▼
docker compose run --rm dev pytest
   │  which means
   ▼
"start a throwaway container from the dev image, run pytest inside it,
 then delete the container (--rm)"
```

---

## 3. Our setup: one container, no database server

```text
                 YOUR COMPUTER (host)
                        │
          ┌─────────────┴──────────────┐
          │                            │
          ▼                            ▼
       Docker                      TablePlus
          │                            │
          ▼                            │
┌────────────────────────┐             │
│ dev container          │             │
│                        │             │
│ Python 3.13            │             │
│ DuckDB (Python library)│             │
│ dbt                    │             │
│ pytest                 │             │
└───────────┬────────────┘             │
            │ reads/writes             │ opens the same file
            ▼                          │
   warehouse/warehouse.duckdb  ◄───────┘
```

Why only **one** container? Python, DuckDB, dbt and pytest are all just
Python packages; they work together in one environment. Separate containers
would add networking and configuration without teaching anything.

Why **no DuckDB container** and no port like `5432`? DuckDB is not a server.
It's a library that runs inside whatever process uses it (our Python
scripts, dbt, TablePlus) and stores everything in a single file. There is
nothing to "connect to over the network".

---

## 4. Bind mounts: why your warehouse survives

A container's own filesystem is thrown away when the container is deleted.
If the warehouse file lived *only* inside the container, every
`make` command would start with an empty warehouse.

Instead, [`compose.yaml`](../../compose.yaml) uses a **bind mount**:

```yaml
volumes:
  - .:/workspace
```

This says: "the project folder on my computer (`.`) **is** the folder
`/workspace` inside the container". Not a copy — the same files.

```text
HOST (your computer)                           CONTAINER
~/.../data-warehouse/warehouse/warehouse.duckdb
              │
              │ bind mount (same file, two names)
              ▼
                                      /workspace/warehouse/warehouse.duckdb
```

Consequences:

- When `make load` writes `/workspace/warehouse/warehouse.duckdb` inside the
  container, the file appears in `warehouse/` on your computer.
- When the container is deleted (after every `make` command, or with
  `make down` / `docker compose down`), the file stays on your disk.
- TablePlus, running on your computer, can open that file directly.
- When you edit a script on your computer, the container sees the change
  immediately — no rebuild needed. You only rebuild (`make build`) when
  `requirements.txt` or the `Dockerfile` changes.

You can check it yourself:

```bash
make load
make down                   # removes containers and networks
ls -lh warehouse/           # warehouse.duckdb is still there
make query                  # and it still has its tables
```

### Who owns the files?

The Makefile passes your user id (`id -u`) to Compose, and the container
runs as that user. On Linux this keeps generated files owned by you rather
than by `root`. On macOS it makes no visible difference.

---

## 5. DuckDB + TablePlus: one writer at a time

DuckDB's rule is simple:

```text
ONE process may open the file for writing          (make load, later dbt run)
   OR
MANY processes may open it read-only               (make query, TablePlus in read-only mode)
   — but not both at the same time.
```

So, in practice:

1. **Disconnect / close the connection in TablePlus before running
   `make load`** (and later the dbt commands). This is a habit you must keep
   yourself — see the warning below.
2. Run one writing command at a time.
3. `make query` opens the file **read-only**, so it can't damage anything.

> **Warning — the lock does not cross the host/container boundary.**
> DuckDB enforces "one writer" with a file lock. We tested this project's
> setup (macOS + OrbStack bind mount, 2026-10-05):
>
> - Two **containers** at once → the second one fails cleanly with
>   `IO Error: Could not set lock on file ... Conflicting lock is held`.
>   DuckDB protects you.
> - A process on your **Mac** (like TablePlus) holding the file open while a
>   **container** writes → *no error at all*; both proceed. The lock is not
>   visible across the boundary, so nothing stops two writers from
>   corrupting the file, and TablePlus may show stale data.
>
> So: **disconnect TablePlus → run the `make` command → reconnect TablePlus.**
> If the warehouse ever looks broken, it is disposable: `make clean`,
> `make generate-data`, `make load` rebuild it exactly.

### Opening the warehouse in TablePlus

1. Run `make generate-data` and `make load` first.
2. In TablePlus: **Create a new connection… → DuckDB**.
3. Pick the file `warehouse/warehouse.duckdb` inside this project folder.
4. Connect. TablePlus first shows DuckDB's default schema, **`main`, which
   is empty** — our tables live in schema **`raw`**. Switch the schema to
   `raw` (TablePlus' schema/database switcher), or open a SQL tab and run
   `SELECT * FROM raw.orders LIMIT 10;` — always write the `raw.` prefix.

TablePlus is for **inspecting and practicing SQL**. Changes to the warehouse
itself should happen through the project's scripts (and later dbt), so they
are reproducible.

> Compatibility note: DuckDB (v1.0–v1.5) writes database files in a storage
> format that every DuckDB 1.x reader understands, so TablePlus' built-in
> DuckDB driver can open files created by the newer DuckDB in our container.

---

## 6. Command reference

| Command | What it does | Writes to the warehouse? |
|---|---|---|
| `make build` | Build the image from the Dockerfile | no |
| `make generate-data` | Write `data/source/*.csv` | no |
| `make load` | Full-refresh CSVs into `raw.*` tables | **yes** |
| `make query SQL="..."` | Run one query, read-only | no |
| `make test` | Run the Python tests (they use temporary files) | no |
| `make shell` | Open a bash shell in the container | — |
| `make versions` | Show Python / DuckDB / dbt / pytest versions | no |
| `make down` | Remove leftover containers/networks | no (your files stay) |
| `make clean` | **Delete** the CSVs and the warehouse file | deletes it |

---

## 7. Common beginner mistakes

- **Expecting `docker compose up` to start a database.** There is no
  database server here. Use the `make` commands.
- **Leaving TablePlus connected while loading.** You'll get a lock error.
  Disconnect first.
- **Rebuilding the image after every code change.** Not needed: the project
  folder is mounted, so changes are visible immediately. Rebuild only when
  dependencies change.
- **Thinking `docker compose down` deletes the warehouse.** It doesn't —
  only `make clean` deletes it.

---

## 8. Before continuing, I should be able to explain:

```text
□ What is the difference between an image and a container?
□ What does a bind mount do?
□ Why does warehouse.duckdb survive `docker compose down`?
□ Why is there no DuckDB server container?
□ Why should TablePlus be disconnected before `make load`?
```
