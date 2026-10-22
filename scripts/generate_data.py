"""Generate a small, deterministic, synthetic e-commerce *source system*.

Pretend this is an export from the database behind an online shop's website:

    customers    -> who has an account
    products     -> what we sell
    orders       -> one row per checkout ("order header")
    order_items  -> one row per product line inside an order
    payments     -> one row per payment event (attempt, success, refund)

Everything is generated from a fixed random seed, so running this script
twice produces byte-for-byte identical CSV files. That makes the numbers in
the tutorials reproducible: your "revenue for March 2026" will match mine.

Usage (inside the Docker container -- see `make generate-data`):

    python scripts/generate_data.py
    python scripts/generate_data.py --seed 7 --output-dir /tmp/other
"""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

try:  # Works both as `python scripts/generate_data.py` and as an import in tests.
    from scripts.source_schema import SOURCE_TABLES
except ModuleNotFoundError:  # pragma: no cover
    from source_schema import SOURCE_TABLES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "source"
DEFAULT_SEED = 42

# The "story" of our shop covers 21 months of orders.
FIRST_ORDER_MONTH = date(2025, 1, 1)
LAST_ORDER_DAY = date(2026, 9, 30)
# The moment the shop's database was exported. Nothing in the files can have
# happened after this -- an order shipped on Sep 30 is still "shipped" here.
EXTRACTED_AT = datetime(2026, 10, 1, 0, 0, 0)
SHOP_OPENED = date(2024, 7, 1)  # customers start signing up here
PRICE_CHANGE_DAY = date(2026, 1, 1)  # some products get more expensive
DISCONTINUED_DAY = date(2026, 3, 1)  # inactive products stop selling here

NUM_CUSTOMERS = 800
# Alice (customer 1) buys a laptop and two mice at this moment. The tutorials
# use this order as their running example.
ALICE_EXAMPLE_ORDER_AT = datetime(2026, 1, 15, 20, 30, 0)
CENT = Decimal("0.01")

# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------

# (city, region, relative popularity)
CITIES = [
    ("Ho Chi Minh City", "South", 30),
    ("Ha Noi", "North", 25),
    ("Da Nang", "Central", 10),
    ("Hai Phong", "North", 7),
    ("Can Tho", "South", 6),
    ("Bien Hoa", "South", 5),
    ("Hue", "Central", 5),
    ("Nha Trang", "Central", 5),
    ("Vung Tau", "South", 4),
    ("Ha Long", "North", 3),
]

FIRST_NAMES = [
    "An", "Binh", "Chi", "Dung", "Giang", "Hai", "Hanh", "Hoa", "Hung", "Khanh",
    "Lan", "Linh", "Long", "Mai", "Minh", "Nam", "Ngoc", "Phuong", "Quang", "Son",
    "Thao", "Trang", "Tuan", "Vy", "Yen", "Bao", "Duc", "Huong", "Kiet", "Thu",
]
LAST_NAMES = [
    "Nguyen", "Tran", "Le", "Pham", "Hoang", "Phan", "Vu", "Dang", "Bui", "Do",
    "Ho", "Ngo", "Duong", "Ly", "Truong", "Dinh",
]

# (segment, relative share)
SEGMENTS = [("standard", 75), ("premium", 18), ("business", 7)]

CATEGORY_SKU_PREFIX = {
    "Electronics": "ELEC",
    "Computers": "COMP",
    "Home & Kitchen": "HOME",
    "Books": "BOOK",
    "Sports & Outdoors": "SPRT",
    "Beauty & Personal Care": "BEAU",
}

# How attractive each category is at the start (month 0) and end (month 20)
# of our story. Linear interpolation in between. This creates growing
# categories (Home & Kitchen, Beauty) and a shrinking one (Books).
CATEGORY_TREND = {
    "Electronics": (1.00, 1.00),
    "Computers": (0.80, 0.80),
    "Home & Kitchen": (0.60, 1.40),
    "Books": (0.90, 0.45),
    "Sports & Outdoors": (0.55, 0.85),
    "Beauty & Personal Care": (0.50, 1.00),
}

# (name, category, brand, list price at launch, launched on, still active?)
PRODUCT_CATALOG = [
    ("Wireless Earbuds", "Electronics", "Voltix", "59.00", None, True),
    ("Noise-Cancelling Headphones", "Electronics", "Sonora", "199.00", None, True),
    ("Bluetooth Speaker", "Electronics", "Sonora", "79.00", None, True),
    ("Smartwatch", "Electronics", "Voltix", "249.00", None, True),
    ("Power Bank 20000mAh", "Electronics", "Voltix", "35.00", None, True),
    ("Phone Case", "Electronics", "Voltix", "15.00", None, True),
    ("USB-C Charger 65W", "Electronics", "Voltix", "29.00", None, True),
    ("Action Camera", "Electronics", "Voltix", "299.00", date(2025, 5, 1), True),
    ("E-Reader", "Electronics", "Sonora", "139.00", None, True),
    ("Fitness Tracker", "Electronics", "Voltix", "89.00", None, False),
    ("Laptop 14-inch", "Computers", "Nimbus", "1099.00", None, True),
    ("Laptop 16-inch Pro", "Computers", "Nimbus", "1799.00", None, True),
    ("Wireless Mouse", "Computers", "Keystone", "25.00", None, True),
    ("Mechanical Keyboard", "Computers", "Keystone", "89.00", None, True),
    ("27-inch Monitor", "Computers", "Nimbus", "329.00", None, True),
    ("USB-C Hub", "Computers", "Keystone", "45.00", None, True),
    ("Webcam 1080p", "Computers", "Keystone", "59.00", None, True),
    ("Laptop Stand", "Computers", "Keystone", "39.00", None, True),
    ("External SSD 1TB", "Computers", "Nimbus", "119.00", None, True),
    ("Mouse Pad XL", "Computers", "Keystone", "12.00", None, True),
    ("Coffee Maker", "Home & Kitchen", "Aurora Home", "89.00", None, True),
    ("Electric Kettle", "Home & Kitchen", "Aurora Home", "39.00", None, True),
    ("Blender", "Home & Kitchen", "Aurora Home", "69.00", None, True),
    ("Air Fryer", "Home & Kitchen", "Aurora Home", "129.00", None, True),
    ("Chef Knife Set", "Home & Kitchen", "Casa Verde", "79.00", None, True),
    ("Non-Stick Pan Set", "Home & Kitchen", "Casa Verde", "99.00", None, True),
    ("Ceramic Dinnerware Set", "Home & Kitchen", "Casa Verde", "59.00", None, True),
    ("Robot Vacuum", "Home & Kitchen", "Aurora Home", "349.00", date(2025, 3, 1), True),
    ("Rice Cooker", "Home & Kitchen", "Aurora Home", "79.00", None, True),
    ("Scented Candle", "Home & Kitchen", "Casa Verde", "18.00", None, True),
    ("Learning SQL Step by Step", "Books", "PageTurner Press", "45.00", None, True),
    ("The Analytics Handbook", "Books", "PageTurner Press", "39.00", None, True),
    ("Python for Beginners", "Books", "PageTurner Press", "35.00", None, True),
    ("Mystery at Ha Long Bay", "Books", "Blue Owl Books", "16.00", None, True),
    ("Cooking Vietnamese at Home", "Books", "Blue Owl Books", "28.00", None, True),
    ("The Startup Playbook", "Books", "PageTurner Press", "24.00", None, True),
    ("Mindful Mornings", "Books", "Blue Owl Books", "19.00", None, True),
    ("Children's Picture Atlas", "Books", "Blue Owl Books", "22.00", None, True),
    ("Science Fiction Anthology", "Books", "Blue Owl Books", "18.00", None, True),
    ("History of Southeast Asia", "Books", "PageTurner Press", "32.00", None, False),
    ("Yoga Mat", "Sports & Outdoors", "PeakFit", "29.00", None, True),
    ("Running Shoes", "Sports & Outdoors", "PeakFit", "99.00", None, True),
    ("Insulated Water Bottle", "Sports & Outdoors", "TrailMark", "25.00", None, True),
    ("Hiking Backpack 30L", "Sports & Outdoors", "TrailMark", "79.00", None, True),
    ("2-Person Tent", "Sports & Outdoors", "TrailMark", "149.00", None, True),
    ("Adjustable Dumbbells", "Sports & Outdoors", "PeakFit", "189.00", None, True),
    ("Resistance Bands Set", "Sports & Outdoors", "PeakFit", "19.00", None, True),
    ("Cycling Helmet", "Sports & Outdoors", "TrailMark", "59.00", None, True),
    ("Jump Rope", "Sports & Outdoors", "PeakFit", "12.00", None, True),
    ("Camping Lantern", "Sports & Outdoors", "TrailMark", "29.00", None, True),
    ("Vitamin C Serum", "Beauty & Personal Care", "Lumina", "32.00", None, True),
    ("Sunscreen SPF50", "Beauty & Personal Care", "Lumina", "18.00", None, True),
    ("Daily Moisturizer", "Beauty & Personal Care", "Lumina", "26.00", None, True),
    ("Shampoo & Conditioner Set", "Beauty & Personal Care", "Bloom", "22.00", None, True),
    ("Electric Toothbrush", "Beauty & Personal Care", "Bloom", "69.00", None, True),
    ("Hair Dryer", "Beauty & Personal Care", "Bloom", "79.00", None, True),
    ("Lip Balm Trio", "Beauty & Personal Care", "Bloom", "9.00", None, True),
    ("Eau de Parfum 50ml", "Beauty & Personal Care", "Lumina", "85.00", date(2025, 9, 1), True),
    ("Face Mask Pack", "Beauty & Personal Care", "Lumina", "15.00", None, True),
    ("Beard Trimmer", "Beauty & Personal Care", "Bloom", "49.00", None, True),
]


# --------------------------------------------------------------------------
# In-memory records (written to CSV at the end)
# --------------------------------------------------------------------------


@dataclass
class Customer:
    customer_id: int
    first_name: str
    last_name: str
    email: str
    city: str
    region: str
    customer_segment: str
    created_at: datetime
    updated_at: datetime
    activity: float  # how often this customer shops (not exported)


@dataclass
class Product:
    product_id: int
    sku: str
    product_name: str
    category: str
    brand: str
    launch_price: Decimal  # price before PRICE_CHANGE_DAY (not exported)
    list_price: Decimal  # current price
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def price_on(self, day: date) -> Decimal:
        return self.launch_price if day < PRICE_CHANGE_DAY else self.list_price

    def sellable_on(self, day: date) -> bool:
        if day < self.created_at.date():
            return False
        return self.is_active or day < DISCONTINUED_DAY


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def random_datetime(rng: random.Random, start: date, end: date) -> datetime:
    """A random moment between start 00:00 and end 23:59:59 (inclusive days)."""
    days = (end - start).days
    day = start + timedelta(days=rng.randint(0, days))
    # Shoppers mostly buy between 08:00 and 23:00.
    hour = rng.choices(range(24), weights=[1] * 8 + [4] * 15 + [2])[0]
    return datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59))


def month_starts(first: date, last: date) -> list[date]:
    months, current = [], first
    while current <= last:
        months.append(current)
        current = date(current.year + current.month // 12, current.month % 12 + 1, 1)
    return months


# --------------------------------------------------------------------------
# Generators
# --------------------------------------------------------------------------


def build_customers(rng: random.Random) -> list[Customer]:
    customers: list[Customer] = []
    city_names = [c for c, _, _ in CITIES]
    city_region = {c: r for c, r, _ in CITIES}
    city_weights = [w for _, _, w in CITIES]
    open_days = (LAST_ORDER_DAY - timedelta(days=5) - SHOP_OPENED).days

    for customer_id in range(1, NUM_CUSTOMERS + 1):
        if customer_id == 1:
            # Alice is our recurring example customer (see the SCD tutorial).
            first, last, city, segment = "Alice", "Nguyen", "Ho Chi Minh City", "premium"
            created_at = datetime(2024, 7, 3, 10, 15, 0)
            activity = 6.0
        else:
            first = rng.choice(FIRST_NAMES)
            last = rng.choice(LAST_NAMES)
            city = rng.choices(city_names, weights=city_weights)[0]
            segment = rng.choices([s for s, _ in SEGMENTS], weights=[w for _, w in SEGMENTS])[0]
            # rng.random() ** 0.7 is skewed towards 1.0 -> more recent sign-ups
            # (the shop is growing).
            offset = int(open_days * rng.random() ** 0.7)
            created_at = random_datetime(
                rng, SHOP_OPENED + timedelta(days=offset), SHOP_OPENED + timedelta(days=offset)
            )
            # A few customers are very loyal, most buy occasionally.
            activity = min(rng.paretovariate(1.6), 25.0)

        # Some customers edited their profile later (e.g. moved city). The
        # source system only keeps the CURRENT values -- the old ones are gone.
        updated_at = created_at
        if customer_id != 1 and rng.random() < 0.15:
            latest = LAST_ORDER_DAY
            if created_at.date() + timedelta(days=30) < latest:
                updated_at = random_datetime(rng, created_at.date() + timedelta(days=30), latest)

        customers.append(
            Customer(
                customer_id=customer_id,
                first_name=first,
                last_name=last,
                email=f"{first}.{last}.{customer_id}@example.com".lower(),
                city=city,
                region=city_region[city],
                customer_segment=segment,
                created_at=created_at,
                updated_at=updated_at,
                activity=activity,
            )
        )
    return customers


def build_products(rng: random.Random) -> list[Product]:
    products: list[Product] = []
    for product_id, (name, category, brand, price, launched, active) in enumerate(
        PRODUCT_CATALOG, start=1
    ):
        launch_price = Decimal(price)
        created_at = datetime.combine(launched or date(2024, 6, 1), datetime.min.time()).replace(
            hour=9
        )
        updated_at = created_at
        list_price = launch_price
        # About a third of the catalog gets a price increase on PRICE_CHANGE_DAY.
        if created_at.date() < PRICE_CHANGE_DAY and rng.random() < 0.35:
            list_price = money(launch_price * Decimal(str(rng.choice([1.05, 1.08, 1.10, 1.15]))))
            updated_at = datetime.combine(PRICE_CHANGE_DAY, datetime.min.time()).replace(hour=9)
        if not active:
            updated_at = datetime.combine(DISCONTINUED_DAY, datetime.min.time()).replace(hour=9)
        products.append(
            Product(
                product_id=product_id,
                sku=f"{CATEGORY_SKU_PREFIX[category]}-{product_id:04d}",
                product_name=name,
                category=category,
                brand=brand,
                launch_price=launch_price,
                list_price=list_price,
                is_active=active,
                created_at=created_at,
                updated_at=updated_at,
            )
        )
    return products


def orders_in_month(rng: random.Random, month_index: int, month: date) -> int:
    base = 130 * (1.045**month_index)  # ~4.5% growth per month
    seasonal = {11: 1.35, 12: 1.50, 1: 0.90, 2: 0.85}.get(month.month, 1.0)
    noise = rng.uniform(0.92, 1.08)
    return round(base * seasonal * noise)


def pick_status(rng: random.Random, ordered_at: datetime) -> str:
    age_days = (LAST_ORDER_DAY - ordered_at.date()).days
    if age_days <= 3:
        return rng.choices(["pending", "shipped", "cancelled"], weights=[50, 40, 10])[0]
    if age_days <= 10:
        return rng.choices(["shipped", "completed", "cancelled"], weights=[50, 45, 5])[0]
    return rng.choices(["completed", "cancelled"], weights=[91, 9])[0]


def is_promo_day(day: date) -> bool:
    """Black Friday / Cyber Monday week and the 11.11 sale."""
    return (day.month == 11 and (day.day == 11 or day.day >= 24)) or (
        day.month == 12 and day.day <= 2
    )


def generate(output_dir: Path = DEFAULT_OUTPUT_DIR, seed: int = DEFAULT_SEED) -> dict[str, int]:
    """Generate all source CSV files. Returns {table_name: row_count}."""
    rng = random.Random(seed)
    customers = build_customers(rng)
    products = build_products(rng)
    categories = list(CATEGORY_TREND)
    months = month_starts(FIRST_ORDER_MONTH, LAST_ORDER_DAY)

    # 1) Decide WHEN orders happen and WHO places them.
    planned: list[tuple[datetime, int]] = []
    for month_index, month in enumerate(months):
        next_month = month_starts(month, date(month.year + 1, 12, 31))[1]
        month_end = min(next_month - timedelta(days=1), LAST_ORDER_DAY)
        for _ in range(orders_in_month(rng, month_index, month)):
            ordered_at = random_datetime(rng, month, month_end)
            eligible = [c for c in customers if c.created_at < ordered_at]
            customer = rng.choices(eligible, weights=[c.activity for c in eligible])[0]
            planned.append((ordered_at, customer.customer_id))
    planned.append((ALICE_EXAMPLE_ORDER_AT, 1))
    planned.sort()

    # 2) Build orders, their product lines and their payments.
    orders: list[dict] = []
    order_items: list[dict] = []
    payments: list[dict] = []
    order_item_id = 0
    payment_id = 0

    for order_id, (ordered_at, customer_id) in enumerate(planned, start=1001):
        day = ordered_at.date()
        progress = (ordered_at.date() - FIRST_ORDER_MONTH).days / (
            LAST_ORDER_DAY - FIRST_ORDER_MONTH
        ).days
        category_weights = [
            start + (end - start) * progress for start, end in CATEGORY_TREND.values()
        ]
        available = [p for p in products if p.sellable_on(day)]

        if customer_id == 1 and ordered_at == ALICE_EXAMPLE_ORDER_AT:
            # The tutorial example: Laptop x 1 and Mouse x 2.
            basket = [(products[10], 1), (products[12], 2)]
        else:
            num_lines = rng.choices([1, 2, 3, 4], weights=[45, 30, 15, 10])[0]
            basket, chosen_ids = [], set()
            while len(basket) < num_lines:
                category = rng.choices(categories, weights=category_weights)[0]
                candidates = [
                    p for p in available if p.category == category and p.product_id not in chosen_ids
                ]
                if not candidates:
                    continue
                product = rng.choice(candidates)
                price = product.price_on(day)
                if price < 30:
                    quantity = rng.choices([1, 2, 3], weights=[60, 25, 15])[0]
                else:
                    quantity = rng.choices([1, 2], weights=[90, 10])[0]
                basket.append((product, quantity))
                chosen_ids.add(product.product_id)

        order_total = Decimal("0.00")
        discount_chance = 0.40 if is_promo_day(day) else 0.12
        for product, quantity in basket:
            order_item_id += 1
            unit_price = product.price_on(day)
            gross = unit_price * quantity
            discount = Decimal("0.00")
            if rng.random() < discount_chance:
                discount = money(gross * Decimal(str(rng.choice([0.05, 0.10, 0.15, 0.20]))))
            order_total += gross - discount
            order_items.append(
                {
                    "order_item_id": order_item_id,
                    "order_id": order_id,
                    "product_id": product.product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_amount": discount,
                }
            )

        if customer_id == 1 and ordered_at == ALICE_EXAMPLE_ORDER_AT:
            status = "completed"
        else:
            status = pick_status(rng, ordered_at)
        method = rng.choices(
            ["credit_card", "e_wallet", "bank_transfer", "cash_on_delivery"],
            weights=[35, 30, 10, 25],
        )[0]
        delivered_at = ordered_at + timedelta(days=rng.randint(2, 6), hours=rng.randint(0, 10))
        if status == "pending":
            updated_at = ordered_at
        elif status == "shipped":
            updated_at = ordered_at + timedelta(hours=rng.randint(6, 30))
        elif status == "completed":
            updated_at = delivered_at
        else:  # cancelled
            updated_at = ordered_at + timedelta(hours=rng.randint(1, 48))

        # A status change that would happen after the export hasn't happened
        # yet: step back to the previous status.
        if updated_at > EXTRACTED_AT and status == "completed":
            status, updated_at = "shipped", ordered_at + timedelta(hours=12)
        if updated_at > EXTRACTED_AT:
            status, updated_at = "pending", ordered_at

        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_status": status,
                "order_total": order_total,
                "ordered_at": ordered_at,
                "updated_at": updated_at,
            }
        )

        # Payments: one row per payment EVENT.
        events: list[tuple[str, datetime]] = []
        if method == "cash_on_delivery":
            # Cash is only collected when the parcel is delivered.
            if status == "completed":
                events.append(("succeeded", delivered_at))
        else:
            paid_at = ordered_at + timedelta(minutes=rng.randint(1, 15))
            if rng.random() < 0.06:  # card declined / wallet timeout, then retried
                events.append(("failed", ordered_at + timedelta(seconds=rng.randint(20, 50))))
            events.append(("succeeded", paid_at))
            if status == "cancelled":
                events.append(("refunded", updated_at))
        for payment_status, processed_at in events:
            payment_id += 1
            payments.append(
                {
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "payment_method": method,
                    "payment_status": payment_status,
                    "amount": order_total,
                    "processed_at": processed_at,
                }
            )

    tables = {
        "customers": [vars(c) for c in customers],
        "products": [vars(p) for p in products],
        "orders": orders,
        "order_items": order_items,
        "payments": payments,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for table, rows in tables.items():
        write_csv(output_dir / f"{table}.csv", list(SOURCE_TABLES[table]), rows)
    return {table: len(rows) for table, rows in tables.items()}


def format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    # newline="" + lineterminator="\n" -> identical files on every OS.
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow([format_value(row[column]) for column in columns])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed (default: 42)")
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="where to write the CSV files"
    )
    args = parser.parse_args()

    counts = generate(args.output_dir, args.seed)
    print(f"Generated source data with seed {args.seed} in {args.output_dir}:")
    for table, count in counts.items():
        print(f"  {table + '.csv':<17} {count:>6} rows")


if __name__ == "__main__":
    main()
