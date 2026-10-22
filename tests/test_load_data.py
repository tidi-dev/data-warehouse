"""Tests for load_data.py: CSV files -> DuckDB raw schema."""

from pathlib import Path

import duckdb
import pytest

from scripts.generate_data import generate
from scripts.load_data import load
from scripts.source_schema import SOURCE_TABLES


@pytest.fixture(scope="module")
def source_dir(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("source")
    generate(directory, seed=42)
    return directory


def csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # minus the header line


def test_every_csv_row_arrives_in_raw(source_dir, tmp_path):
    """Raw must preserve the source: no rows lost, no rows invented."""
    counts = load(source_dir, tmp_path / "test.duckdb")
    for table in SOURCE_TABLES:
        assert counts[table] == csv_row_count(source_dir / f"{table}.csv")


def test_loading_twice_does_not_duplicate_rows(source_dir, tmp_path):
    """Full refresh is idempotent: same input, same warehouse."""
    database = tmp_path / "test.duckdb"
    first = load(source_dir, database)
    second = load(source_dir, database)
    assert first == second


def test_raw_columns_have_the_declared_types(source_dir, tmp_path):
    """Money must arrive as DECIMAL (exact), not DOUBLE (approximate)."""
    database = tmp_path / "test.duckdb"
    load(source_dir, database)
    with duckdb.connect(str(database), read_only=True) as con:
        for table, columns in SOURCE_TABLES.items():
            actual = dict(
                con.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_schema = 'raw' AND table_name = ?",
                    [table],
                ).fetchall()
            )
            for column, declared in columns.items():
                assert actual[column] == declared.replace(" ", ""), f"raw.{table}.{column}"
            assert {"_source_file", "_loaded_at"} <= set(actual)


def test_missing_source_file_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="make generate-data"):
        load(tmp_path, tmp_path / "test.duckdb")
