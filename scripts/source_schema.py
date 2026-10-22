"""The shape of our fictional e-commerce *source system*.

This file is the single place that says which tables the operational
application has and which columns (with which types) each table contains.

It is used by:
  - generate_data.py  -> to write CSV headers in this exact column order
  - load_data.py      -> to tell DuckDB the type of every column
  - tests/            -> to check that generated files match this contract

The types are DuckDB SQL types. DECIMAL(10, 2) is used for money because
money must be exact; floating point numbers (DOUBLE) can introduce tiny
rounding errors such as 0.1 + 0.2 = 0.30000000000000004.
"""

SOURCE_TABLES: dict[str, dict[str, str]] = {
    # One row = one customer account (its CURRENT state only).
    "customers": {
        "customer_id": "INTEGER",
        "first_name": "VARCHAR",
        "last_name": "VARCHAR",
        "email": "VARCHAR",
        "city": "VARCHAR",
        "region": "VARCHAR",
        "customer_segment": "VARCHAR",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    },
    # One row = one product in the catalog (its CURRENT state only).
    "products": {
        "product_id": "INTEGER",
        "sku": "VARCHAR",
        "product_name": "VARCHAR",
        "category": "VARCHAR",
        "brand": "VARCHAR",
        "list_price": "DECIMAL(10, 2)",
        "is_active": "BOOLEAN",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    },
    # One row = one order (the "header" of a shopping cart checkout).
    "orders": {
        "order_id": "INTEGER",
        "customer_id": "INTEGER",
        "order_status": "VARCHAR",
        "order_total": "DECIMAL(10, 2)",
        "ordered_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    },
    # One row = one product line inside one order.
    "order_items": {
        "order_item_id": "INTEGER",
        "order_id": "INTEGER",
        "product_id": "INTEGER",
        "quantity": "INTEGER",
        "unit_price": "DECIMAL(10, 2)",
        "discount_amount": "DECIMAL(10, 2)",
    },
    # One row = one payment event (an attempt, a success, or a refund).
    "payments": {
        "payment_id": "INTEGER",
        "order_id": "INTEGER",
        "payment_method": "VARCHAR",
        "payment_status": "VARCHAR",
        "amount": "DECIMAL(10, 2)",
        "processed_at": "TIMESTAMP",
    },
}

ORDER_STATUSES = ("pending", "shipped", "completed", "cancelled")
PAYMENT_METHODS = ("credit_card", "e_wallet", "bank_transfer", "cash_on_delivery")
PAYMENT_STATUSES = ("succeeded", "failed", "refunded")
CUSTOMER_SEGMENTS = ("standard", "premium", "business")
