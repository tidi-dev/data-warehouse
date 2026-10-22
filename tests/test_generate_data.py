"""Tests for our ASSUMPTIONS about the generated source data.

Each test protects something the tutorials (and later the warehouse) rely
on. If one of these fails, the lessons and their numbers would be wrong.
"""

import csv
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.generate_data import generate
from scripts.source_schema import ORDER_STATUSES, PAYMENT_METHODS, PAYMENT_STATUSES, SOURCE_TABLES


def read_rows(directory: Path, table: str) -> list[dict[str, str]]:
    with (directory / f"{table}.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def source_dir(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("source")
    generate(directory, seed=42)
    return directory


@pytest.fixture(scope="module")
def tables(source_dir) -> dict[str, list[dict[str, str]]]:
    return {table: read_rows(source_dir, table) for table in SOURCE_TABLES}


# --- Reproducibility -------------------------------------------------------


def test_same_seed_produces_identical_files(source_dir, tmp_path):
    """The tutorials quote numbers; everyone must get the same data."""
    generate(tmp_path, seed=42)
    for table in SOURCE_TABLES:
        assert (tmp_path / f"{table}.csv").read_bytes() == (
            source_dir / f"{table}.csv"
        ).read_bytes(), f"{table}.csv differs between two runs with the same seed"


def test_different_seed_produces_different_data(source_dir, tmp_path):
    generate(tmp_path, seed=7)
    assert (tmp_path / "orders.csv").read_bytes() != (source_dir / "orders.csv").read_bytes()


# --- Shape: the contract with load_data.py ---------------------------------


@pytest.mark.parametrize("table", SOURCE_TABLES)
def test_csv_header_matches_source_schema(source_dir, table):
    with (source_dir / f"{table}.csv").open(encoding="utf-8") as f:
        header = f.readline().strip().split(",")
    assert header == list(SOURCE_TABLES[table])


@pytest.mark.parametrize("table", SOURCE_TABLES)
def test_tables_are_not_empty(tables, table):
    assert len(tables[table]) > 0


@pytest.mark.parametrize(
    "table, key",
    [
        ("customers", "customer_id"),
        ("products", "product_id"),
        ("orders", "order_id"),
        ("order_items", "order_item_id"),
        ("payments", "payment_id"),
    ],
)
def test_primary_keys_are_unique(tables, table, key):
    """A duplicated id would mean one 'thing' is counted twice."""
    counts = Counter(row[key] for row in tables[table])
    duplicates = [value for value, n in counts.items() if n > 1]
    assert not duplicates, f"duplicate {key} values in {table}: {duplicates[:5]}"


# --- Relationships between tables -------------------------------------------


@pytest.mark.parametrize(
    "child, foreign_key, parent, parent_key",
    [
        ("orders", "customer_id", "customers", "customer_id"),
        ("order_items", "order_id", "orders", "order_id"),
        ("order_items", "product_id", "products", "product_id"),
        ("payments", "order_id", "orders", "order_id"),
    ],
)
def test_foreign_keys_point_to_existing_rows(tables, child, foreign_key, parent, parent_key):
    """An order_item for a product that doesn't exist could never get a category."""
    known = {row[parent_key] for row in tables[parent]}
    orphans = {row[foreign_key] for row in tables[child]} - known
    assert not orphans, f"{child}.{foreign_key} values missing from {parent}: {sorted(orphans)[:5]}"


def test_every_order_has_at_least_one_item(tables):
    orders_with_items = {row["order_id"] for row in tables["order_items"]}
    assert {row["order_id"] for row in tables["orders"]} == orders_with_items


def test_a_product_appears_at_most_once_per_order(tables):
    """One order_items row = one product line, so (order, product) is unique."""
    pairs = Counter((row["order_id"], row["product_id"]) for row in tables["order_items"])
    assert max(pairs.values()) == 1


def test_customers_order_only_after_signing_up(tables):
    created = {row["customer_id"]: row["created_at"] for row in tables["customers"]}
    early = [row["order_id"] for row in tables["orders"] if row["ordered_at"] <= created[row["customer_id"]]]
    assert not early


# --- Money --------------------------------------------------------------------


def test_order_total_equals_sum_of_its_lines(tables):
    """orders.order_total is a header-level copy of the line amounts.

    line net amount = quantity * unit_price - discount_amount
    """
    line_totals: dict[str, Decimal] = {}
    for row in tables["order_items"]:
        net = int(row["quantity"]) * Decimal(row["unit_price"]) - Decimal(row["discount_amount"])
        line_totals[row["order_id"]] = line_totals.get(row["order_id"], Decimal("0")) + net
    mismatches = [
        row["order_id"]
        for row in tables["orders"]
        if Decimal(row["order_total"]) != line_totals[row["order_id"]]
    ]
    assert not mismatches


def test_line_amounts_are_sensible(tables):
    for row in tables["order_items"]:
        quantity = int(row["quantity"])
        gross = quantity * Decimal(row["unit_price"])
        assert quantity >= 1
        assert Decimal(row["unit_price"]) > 0
        assert Decimal("0") <= Decimal(row["discount_amount"]) < gross


def test_completed_orders_are_paid_exactly_once(tables):
    """Successful payments minus refunds should equal the order total for
    completed orders -- otherwise payment-based revenue would not reconcile."""
    paid: Counter = Counter()
    for row in tables["payments"]:
        if row["payment_status"] == "succeeded":
            paid[row["order_id"]] += 1
        elif row["payment_status"] == "refunded":
            paid[row["order_id"]] -= 1
    completed = [row["order_id"] for row in tables["orders"] if row["order_status"] == "completed"]
    assert all(paid[order_id] == 1 for order_id in completed)


# --- Allowed values -------------------------------------------------------------


@pytest.mark.parametrize(
    "table, column, allowed",
    [
        ("orders", "order_status", ORDER_STATUSES),
        ("payments", "payment_method", PAYMENT_METHODS),
        ("payments", "payment_status", PAYMENT_STATUSES),
    ],
)
def test_status_columns_only_contain_known_values(tables, table, column, allowed):
    assert {row[column] for row in tables[table]} <= set(allowed)


# --- Enough variety for the lessons ---------------------------------------------


def test_data_supports_the_analytical_questions(tables):
    """The tutorials ask about months, categories, regions and baskets."""
    months = {row["ordered_at"][:7] for row in tables["orders"]}
    categories = {row["category"] for row in tables["products"]}
    regions = {row["region"] for row in tables["customers"]}
    lines_per_order = Counter(row["order_id"] for row in tables["order_items"])

    assert len(months) >= 12, "need at least a year of orders for month-over-month analysis"
    assert len(categories) >= 5
    assert len(regions) >= 3
    assert any(n > 1 for n in lines_per_order.values()), "need multi-product orders"
    assert len(set(row["order_status"] for row in tables["orders"])) > 1


def test_alice_example_order_exists(tables):
    """The tutorials use Alice's January 2026 order (Laptop x 1, Mouse x 2)."""
    alice = next(row for row in tables["customers"] if row["customer_id"] == "1")
    assert (alice["first_name"], alice["city"]) == ("Alice", "Ho Chi Minh City")

    order = next(
        row
        for row in tables["orders"]
        if row["customer_id"] == "1" and row["ordered_at"] == "2026-01-15 20:30:00"
    )
    products = {row["product_id"]: row["product_name"] for row in tables["products"]}
    lines = {
        products[row["product_id"]]: int(row["quantity"])
        for row in tables["order_items"]
        if row["order_id"] == order["order_id"]
    }
    assert lines == {"Laptop 14-inch": 1, "Wireless Mouse": 2}


def test_nothing_happens_after_the_export(tables):
    """The files are a snapshot taken at 2026-10-01 00:00. A timestamp after
    that would be a change the export could not have seen."""
    export = "2026-10-01 00:00:00"
    late = [
        (table, row[column])
        for table, column in [
            ("orders", "ordered_at"),
            ("orders", "updated_at"),
            ("payments", "processed_at"),
            ("customers", "updated_at"),
        ]
        for row in tables[table]
        if row[column] > export
    ]
    assert not late, late[:5]
