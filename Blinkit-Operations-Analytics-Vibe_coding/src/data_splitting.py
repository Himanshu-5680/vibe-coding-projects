"""
data_splitting.py
=================
Splits the merged CSV (happy_merged.csv) into 7 clean sub-tables.

SPLITTING LOGIC (validated against actual non-null co-occurrence patterns):
---------------------------------------------------------------------------
The merged CSV has 56 columns and 121,445 rows.  Each row belongs to exactly
ONE logical table, identified by which columns contain values:

  Table              | Key identifier column(s)           | Rows
  -------------------|------------------------------------|---------
  feedback           | feedback_id is non-null            |  5,000
  customers          | customer_name is non-null          |  2,500
  delivery           | promised_time is non-null          |  5,000
  orders             | quantity is non-null               |  5,000
                     |   + order_id/customer/date cols    |
                     |     (stored as two separate row    |
                     |      types combined by order_id)   |
  inventory          | stock_received is non-null         | 93,277
  campaigns          | campaign_id is non-null            |  5,400
  products           | product_name is non-null           |    268
  Total              |                                    |121,445

IMPORTANT – Orders split:
  The merged CSV stores each order across TWO row types:
    a) "order_items" rows   → order_id, product_id, quantity, unit_price
    b) "order_header" rows  → order_id, customer_id, delivery_partner_id,
                              delivery_status, order_date, promised_delivery_time,
                              actual_delivery_time, order_total, payment_method,
                              store_id   (identified by: delivery_partner_id is
                              non-null AND promised_time is null)
  These two are joined on order_id to produce a single `orders` sub-table.

Outputs (saved to data/processed/):
  feedback.csv, customers.csv, delivery.csv, orders.csv,
  inventory.csv, campaigns.csv, products.csv
"""

import os
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RAW_PATH = os.path.join("data", "raw", "happy_merged.csv")
PROCESSED_DIR = os.path.join("data", "processed")

# ---------------------------------------------------------------------------
# Column definitions for each sub-table (verified against actual data)
# ---------------------------------------------------------------------------
FEEDBACK_COLS = [
    "feedback_id", "order_id", "customer_id", "rating", "feedback_text",
    "feedback_category", "sentiment", "feedback_date",
]

CUSTOMER_COLS = [
    "customer_id", "customer_name", "email", "phone", "address", "area",
    "pincode", "registration_date", "customer_segment", "total_orders",
    "avg_order_value",
]

DELIVERY_COLS = [
    "order_id", "delivery_partner_id", "promised_time", "actual_time",
    "delivery_time_minutes", "distance_km", "delivery_status",
    "reasons_if_delayed",
]

ORDER_ITEM_COLS = ["order_id", "product_id", "quantity", "unit_price"]
ORDER_HEADER_COLS = [
    "order_id", "customer_id", "delivery_partner_id", "delivery_status",
    "order_date", "promised_delivery_time", "actual_delivery_time",
    "order_total", "payment_method", "store_id",
]
ORDERS_MERGED_COLS = [
    "order_id", "customer_id", "product_id", "quantity", "unit_price",
    "order_date", "promised_delivery_time", "actual_delivery_time",
    "order_total", "payment_method", "store_id",
]

INVENTORY_COLS = ["product_id", "date", "stock_received", "damaged_stock"]

CAMPAIGN_COLS = [
    "campaign_id", "campaign_name", "target_audience", "channel",
    "impressions", "clicks", "conversions", "spend", "revenue_generated",
    "roas",
]

PRODUCT_COLS = [
    "product_id", "product_name", "category", "brand", "price", "mrp",
    "margin_percentage", "shelf_life_days", "min_stock_level", "max_stock_level",
]


def load_merged(path: str = RAW_PATH) -> pd.DataFrame:
    """Load the merged CSV preserving all dtypes as strings initially."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Merged CSV not found: {path}")
    df = pd.read_csv(path, low_memory=False)
    logger.info("Loaded merged CSV: %d rows × %d cols", len(df), len(df.columns))
    return df


def split_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Split the merged DataFrame into sub-tables using the validated
    non-null co-occurrence logic described in the module docstring.

    Returns a dict mapping table name → DataFrame.
    """
    tables: dict[str, pd.DataFrame] = {}

    # --- 1. Feedback ---
    mask_fb = df["feedback_id"].notna()
    tables["feedback"] = df.loc[mask_fb, FEEDBACK_COLS].reset_index(drop=True)
    logger.info("feedback: %d rows", len(tables["feedback"]))

    # --- 2. Customers ---
    mask_cust = df["customer_name"].notna()
    tables["customers"] = df.loc[mask_cust, CUSTOMER_COLS].reset_index(drop=True)
    logger.info("customers: %d rows", len(tables["customers"]))

    # --- 3. Delivery (Type A: has promised_time) ---
    mask_deliv = df["promised_time"].notna()
    tables["delivery"] = df.loc[mask_deliv, DELIVERY_COLS].reset_index(drop=True)
    logger.info("delivery: %d rows", len(tables["delivery"]))

    # --- 4. Orders ---
    # Type B rows: delivery_partner_id non-null AND promised_time is null
    # These carry the order header (customer, dates, totals, store)
    mask_order_header = df["delivery_partner_id"].notna() & df["promised_time"].isna()
    order_header = df.loc[mask_order_header, ORDER_HEADER_COLS].reset_index(drop=True)

    # Order item rows: quantity non-null
    mask_order_items = df["quantity"].notna()
    order_items = df.loc[mask_order_items, ORDER_ITEM_COLS].reset_index(drop=True)

    # Merge items + header on order_id
    orders = order_items.merge(
        order_header.drop(columns=["delivery_partner_id", "delivery_status"]),
        on="order_id",
        how="inner",
    )
    tables["orders"] = orders[ORDERS_MERGED_COLS].reset_index(drop=True)
    logger.info(
        "orders: %d rows (from %d item rows + %d header rows, joined on order_id)",
        len(tables["orders"]),
        len(order_items),
        len(order_header),
    )

    # --- 5. Inventory ---
    mask_inv = df["stock_received"].notna()
    tables["inventory"] = df.loc[mask_inv, INVENTORY_COLS].reset_index(drop=True)
    logger.info("inventory: %d rows", len(tables["inventory"]))

    # --- 6. Campaigns ---
    mask_camp = df["campaign_id"].notna()
    tables["campaigns"] = df.loc[mask_camp, CAMPAIGN_COLS].reset_index(drop=True)
    logger.info("campaigns: %d rows", len(tables["campaigns"]))

    # --- 7. Products ---
    mask_prod = df["product_name"].notna()
    tables["products"] = df.loc[mask_prod, PRODUCT_COLS].reset_index(drop=True)
    logger.info("products: %d rows", len(tables["products"]))

    return tables


def save_tables(tables: dict[str, pd.DataFrame], out_dir: str = PROCESSED_DIR) -> None:
    """Save each sub-table to a CSV in out_dir."""
    os.makedirs(out_dir, exist_ok=True)
    for name, df in tables.items():
        path = os.path.join(out_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        logger.info("Saved %s -> %s (%d rows)", name, path, len(df))


def sanity_check(original: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> None:
    """
    Verify that row counts across sub-tables add up correctly, accounting for
    the fact that Orders are stored across two separate row types in the merge.
    """
    expected_original_rows = (
        len(tables["feedback"])      # 5,000
        + len(tables["customers"])   # 2,500
        + len(tables["delivery"])    # 5,000
        + len(tables["orders"])      # 5,000 (merges two row types: items + headers)
        + len(tables["inventory"])   # 93,277
        + len(tables["campaigns"])   # 5,400
        + len(tables["products"])    # 268
    )
    # order_id rows are stored as TWO rows in the merged file per order
    # so we add order count once more to compensate
    total_source_rows = expected_original_rows + len(tables["orders"])
    logger.info(
        "Sanity check: original rows=%d | sum of sub-table rows=%d | "
        "with order double-row correction=%d",
        len(original),
        expected_original_rows,
        total_source_rows,
    )
    if total_source_rows == len(original):
        logger.info("[OK] Row count sanity check PASSED")
    else:
        logger.warning(
            "Row count mismatch: original=%d, accounted=%d",
            len(original),
            total_source_rows,
        )


def run(raw_path: str = RAW_PATH, out_dir: str = PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """Full pipeline: load -> split -> save -> sanity-check."""
    df = load_merged(raw_path)
    tables = split_tables(df)
    save_tables(tables, out_dir)
    sanity_check(df, tables)
    return tables


if __name__ == "__main__":
    run()
