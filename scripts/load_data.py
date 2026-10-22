"""Load the source CSV files into DuckDB, into a schema called `raw`.

    data/source/orders.csv  ──►  warehouse/warehouse.duckdb : raw.orders

"Raw" means: keep the data exactly as the source system gave it to us.
We do NOT rename columns, filter rows, fix values or join tables here.
We only add two bookkeeping columns so we can always tell where a row came
from and when it arrived:

    _source_file  -> which CSV file the row was read from
    _loaded_at    -> when this load ran

Every run is a FULL REFRESH: each raw table is dropped and rebuilt from the
CSV files (CREATE OR REPLACE TABLE). Running the load twice with the same
files therefore gives the same result -- it never duplicates rows. All
tables are replaced inside one transaction, so a failed load leaves the
previous warehouse untouched.

Usage (inside the Docker container -- see `make load`):

    python scripts/load_data.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

try:  # Works both as `python scripts/load_data.py` and as an import in tests.
    from scripts.source_schema import SOURCE_TABLES
except ModuleNotFoundError:  # pragma: no cover
    from source_schema import SOURCE_TABLES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "data" / "source"
DEFAULT_DATABASE = PROJECT_ROOT / "warehouse" / "warehouse.duckdb"
RAW_SCHEMA = "raw"


def load(source_dir: Path = DEFAULT_SOURCE_DIR, database: Path = DEFAULT_DATABASE) -> dict[str, int]:
    """Full-refresh every raw table from its CSV file. Returns {table: row_count}."""
    missing = [t for t in SOURCE_TABLES if not (source_dir / f"{t}.csv").exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing source files in {source_dir}: {', '.join(m + '.csv' for m in missing)}. "
            "Run `make generate-data` first."
        )

    database.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with duckdb.connect(str(database)) as con:
        con.execute("BEGIN TRANSACTION")
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {RAW_SCHEMA}")
        for table, columns in SOURCE_TABLES.items():
            csv_path = source_dir / f"{table}.csv"
            # Telling DuckDB the column types (instead of letting it guess)
            # means money stays DECIMAL and a malformed file fails loudly.
            column_types = ", ".join(f"'{name}': '{sql_type}'" for name, sql_type in columns.items())
            con.execute(
                f"""
                CREATE OR REPLACE TABLE {RAW_SCHEMA}.{table} AS
                SELECT
                    *,
                    ? AS _source_file,
                    current_timestamp AS _loaded_at
                FROM read_csv(?, header = true, columns = {{{column_types}}})
                """,
                [csv_path.name, str(csv_path)],
            )
            counts[table] = con.execute(f"SELECT count(*) FROM {RAW_SCHEMA}.{table}").fetchone()[0]
        con.execute("COMMIT")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    args = parser.parse_args()

    counts = load(args.source_dir, args.database)
    print(f"Loaded {args.source_dir} into {args.database} (schema '{RAW_SCHEMA}'):")
    for table, count in counts.items():
        print(f"  {RAW_SCHEMA}.{table:<12} {count:>6} rows")


if __name__ == "__main__":
    main()
