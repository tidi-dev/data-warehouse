"""Run one SQL query against the warehouse and print the result as a table.

This is a small convenience for when you don't have TablePlus open.
The database is opened READ-ONLY, so a query can never change the warehouse.

Usage (inside the Docker container -- see `make query`):

    python scripts/query.py "SELECT count(*) FROM raw.orders"
    SQL="SELECT count(*) FROM raw.orders" python scripts/query.py

With no SQL at all, it lists the tables in the warehouse.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = PROJECT_ROOT / "warehouse" / "warehouse.duckdb"

DEFAULT_SQL = """
SELECT schema_name, table_name, column_count, estimated_size AS approx_rows
FROM duckdb_tables()
ORDER BY schema_name, table_name
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        "sql",
        nargs="?",
        default=os.environ.get("SQL") or DEFAULT_SQL,
        help="SQL to run (default: $SQL, or list the tables)",
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--max-rows", type=int, default=50)
    args = parser.parse_args()

    if not args.database.exists():
        sys.exit(f"{args.database} does not exist yet. Run `make load` first.")

    with duckdb.connect(str(args.database), read_only=True) as con:
        con.sql(args.sql).show(max_rows=args.max_rows, max_width=200)


if __name__ == "__main__":
    main()
