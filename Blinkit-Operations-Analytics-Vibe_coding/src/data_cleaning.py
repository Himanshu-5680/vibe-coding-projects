"""
data_cleaning.py
================
Cleans and validates each sub-table produced by data_splitting.py.

For every sub-table:
  1. Cast columns to the correct data types.
  2. Check for and report missing values.
  3. Check for and report duplicate key records.
  4. Validate numeric ranges.
  5. Validate categorical values.
  6. Validate date/time fields.
  7. Flag referential-integrity issues (orphaned foreign keys).
  8. Perform arithmetic consistency checks (e.g. quantity × unit_price vs order_total).

Data quality findings are returned as a dict of validation reports — they are
LOGGED and REPORTED, never silently corrected.  Only safe, non-destructive
fixes are applied (e.g. type casting, dropping fully-empty rows that slipped
through).
"""

import logging
import os
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.join("data", "processed")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _report(name: str, checks: list[dict]) -> dict:
    """Bundle a table's check results into a report dict."""
    return {"table": name, "checks": checks}


def _check(label: str, passed: bool, detail: str = "") -> dict:
    status = "PASS" if passed else "WARN"
    msg = f"[{status}] {label}"
    if detail:
        msg += f" — {detail}"
    if passed:
        logger.info(msg)
    else:
        logger.warning(msg)
    return {"label": label, "status": status, "detail": detail}


def _parse_dates(series: pd.Series, fmt: str | None = None) -> pd.Series:
    """Parse a date series, returning NaT for unparseable values."""
    return pd.to_datetime(series, format=fmt, errors="coerce", dayfirst=False)


# ---------------------------------------------------------------------------
# Per-table cleaning functions
# ---------------------------------------------------------------------------

def clean_feedback(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    checks = []
    df = df.copy()

    # Types
    df["feedback_id"] = pd.to_numeric(df["feedback_id"], errors="coerce")
    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["feedback_date"] = _parse_dates(df["feedback_date"])

    # Missing values
    for col in ["feedback_id", "order_id", "customer_id", "rating",
                "feedback_category", "sentiment", "feedback_date"]:
        n = df[col].isna().sum()
        checks.append(_check(f"feedback.{col} no nulls", n == 0,
                              f"{n} nulls found" if n else ""))

    # Duplicate feedback_id
    dups = df["feedback_id"].duplicated().sum()
    checks.append(_check("feedback: no duplicate feedback_id", dups == 0,
                          f"{dups} duplicates" if dups else ""))

    # Rating range 1-5
    bad_rating = (~df["rating"].between(1, 5, inclusive="both") & df["rating"].notna()).sum()
    checks.append(_check("feedback: rating in [1,5]", bad_rating == 0,
                          f"{bad_rating} out-of-range" if bad_rating else ""))

    # Sentiment values
    valid_sentiments = {"Positive", "Neutral", "Negative"}
    bad_sent = (~df["sentiment"].isin(valid_sentiments) & df["sentiment"].notna()).sum()
    checks.append(_check("feedback: valid sentiment values", bad_sent == 0,
                          f"{bad_sent} invalid" if bad_sent else ""))

    # feedback_category values
    valid_cats = {"Delivery", "App Experience", "Customer Service", "Product Quality"}
    bad_cat = (~df["feedback_category"].isin(valid_cats) & df["feedback_category"].notna()).sum()
    checks.append(_check("feedback: valid feedback_category", bad_cat == 0,
                          f"{bad_cat} invalid" if bad_cat else ""))

    return df, _report("feedback", checks)


def clean_customers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    checks = []
    df = df.copy()

    # Types
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    df["total_orders"] = pd.to_numeric(df["total_orders"], errors="coerce")
    df["avg_order_value"] = pd.to_numeric(df["avg_order_value"], errors="coerce")
    df["registration_date"] = _parse_dates(df["registration_date"])

    # Missing
    for col in ["customer_id", "customer_name", "customer_segment"]:
        n = df[col].isna().sum()
        checks.append(_check(f"customers.{col} no nulls", n == 0,
                              f"{n} nulls" if n else ""))

    # Duplicate customer_id
    dups = df["customer_id"].duplicated().sum()
    checks.append(_check("customers: no duplicate customer_id", dups == 0,
                          f"{dups} duplicates" if dups else ""))

    # total_orders >= 0
    bad_ord = (df["total_orders"] < 0).sum()
    checks.append(_check("customers: total_orders >= 0", bad_ord == 0,
                          f"{bad_ord} negative" if bad_ord else ""))

    # avg_order_value >= 0
    bad_aov = (df["avg_order_value"] < 0).sum()
    checks.append(_check("customers: avg_order_value >= 0", bad_aov == 0,
                          f"{bad_aov} negative" if bad_aov else ""))

    # Segment values
    valid_segs = {"Premium", "Regular", "New", "Inactive"}
    bad_seg = (~df["customer_segment"].isin(valid_segs) & df["customer_segment"].notna()).sum()
    checks.append(_check("customers: valid segment", bad_seg == 0,
                          f"{bad_seg} invalid" if bad_seg else ""))

    return df, _report("customers", checks)


def clean_delivery(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    checks = []
    df = df.copy()

    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["delivery_partner_id"] = pd.to_numeric(df["delivery_partner_id"], errors="coerce")
    df["delivery_time_minutes"] = pd.to_numeric(df["delivery_time_minutes"], errors="coerce")
    df["distance_km"] = pd.to_numeric(df["distance_km"], errors="coerce")
    df["promised_time"] = _parse_dates(df["promised_time"])
    df["actual_time"] = _parse_dates(df["actual_time"])

    for col in ["order_id", "delivery_partner_id", "delivery_status"]:
        n = df[col].isna().sum()
        checks.append(_check(f"delivery.{col} no nulls", n == 0,
                              f"{n} nulls" if n else ""))

    # Duplicate order_id
    dups = df["order_id"].duplicated().sum()
    checks.append(_check("delivery: no duplicate order_id", dups == 0,
                          f"{dups} duplicates" if dups else ""))

    # delivery_time_minutes — note negative values exist (arrived early)
    # flag extreme negatives
    extreme = (df["delivery_time_minutes"] < -60).sum()
    checks.append(_check("delivery: no extreme negative delivery_time_minutes (<-60)", extreme == 0,
                          f"{extreme} extreme negatives" if extreme else ""))

    # delivery_status values
    valid_status = {"On Time", "Slightly Delayed", "Significantly Delayed"}
    bad_status = (~df["delivery_status"].isin(valid_status) & df["delivery_status"].notna()).sum()
    checks.append(_check("delivery: valid delivery_status", bad_status == 0,
                          f"{bad_status} invalid" if bad_status else ""))

    # Actual after promised (for delayed orders)
    delayed = df[df["delivery_status"] != "On Time"]
    early = (delayed["actual_time"] < delayed["promised_time"]).sum()
    checks.append(_check("delivery: delayed orders — actual_time >= promised_time",
                          early == 0,
                          f"{early} delayed orders with actual < promised" if early else ""))

    return df, _report("delivery", checks)


def clean_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    checks = []
    df = df.copy()

    df["order_id"] = pd.to_numeric(df["order_id"], errors="coerce")
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["order_total"] = pd.to_numeric(df["order_total"], errors="coerce")
    df["store_id"] = pd.to_numeric(df["store_id"], errors="coerce")
    df["order_date"] = _parse_dates(df["order_date"])
    df["promised_delivery_time"] = _parse_dates(df["promised_delivery_time"])
    df["actual_delivery_time"] = _parse_dates(df["actual_delivery_time"])

    for col in ["order_id", "customer_id", "product_id", "quantity",
                "unit_price", "order_total", "order_date"]:
        n = df[col].isna().sum()
        checks.append(_check(f"orders.{col} no nulls", n == 0,
                              f"{n} nulls" if n else ""))

    # Duplicate order_id
    dups = df["order_id"].duplicated().sum()
    checks.append(_check("orders: no duplicate order_id", dups == 0,
                          f"{dups} duplicates" if dups else ""))

    # quantity > 0
    bad_qty = (df["quantity"] <= 0).sum()
    checks.append(_check("orders: quantity > 0", bad_qty == 0,
                          f"{bad_qty} non-positive" if bad_qty else ""))

    # unit_price > 0
    bad_up = (df["unit_price"] <= 0).sum()
    checks.append(_check("orders: unit_price > 0", bad_up == 0,
                          f"{bad_up} non-positive" if bad_up else ""))

    # order_total > 0
    bad_ot = (df["order_total"] <= 0).sum()
    checks.append(_check("orders: order_total > 0", bad_ot == 0,
                          f"{bad_ot} non-positive" if bad_ot else ""))

    # Arithmetic consistency: quantity × unit_price vs order_total
    # NOTE: mismatches are EXPECTED because order_total may include taxes/delivery fees/discounts
    # We flag the count without correcting any values.
    df["_calc_total"] = df["quantity"] * df["unit_price"]
    mismatch = (abs(df["_calc_total"] - df["order_total"]) > 0.01).sum()
    checks.append(_check(
        "orders: order_total == quantity x unit_price",
        mismatch == 0,
        f"{mismatch} mismatches - expected: order_total may include taxes/fees/discounts "
        f"(source data NOT modified)" if mismatch else "",
    ))
    # Keep the calc column for reporting; drop from the saved file
    df = df.drop(columns=["_calc_total"])

    # Payment method values
    valid_pm = {"Cash", "UPI", "Card", "Wallet"}
    bad_pm = (~df["payment_method"].isin(valid_pm) & df["payment_method"].notna()).sum()
    checks.append(_check("orders: valid payment_method", bad_pm == 0,
                          f"{bad_pm} invalid" if bad_pm else ""))

    # actual_delivery_time >= order_date
    bad_date = (df["actual_delivery_time"] < df["order_date"]).sum()
    checks.append(_check("orders: actual_delivery_time >= order_date", bad_date == 0,
                          f"{bad_date} orders with delivery before order date" if bad_date else ""))

    return df, _report("orders", checks)


def clean_inventory(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    checks = []
    df = df.copy()

    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    df["stock_received"] = pd.to_numeric(df["stock_received"], errors="coerce")
    df["damaged_stock"] = pd.to_numeric(df["damaged_stock"], errors="coerce")
    # Date column has mixed formats (e.g. "17-03-2023" and "Sep-24")
    df["date"] = pd.to_datetime(df["date"], format="mixed", dayfirst=True, errors="coerce")

    for col in ["product_id", "date", "stock_received", "damaged_stock"]:
        n = df[col].isna().sum()
        checks.append(_check(f"inventory.{col} no nulls", n == 0,
                              f"{n} nulls/unparseable" if n else ""))

    # stock_received >= 0
    bad_sr = (df["stock_received"] < 0).sum()
    checks.append(_check("inventory: stock_received >= 0", bad_sr == 0,
                          f"{bad_sr} negative" if bad_sr else ""))

    # damaged_stock >= 0
    bad_ds = (df["damaged_stock"] < 0).sum()
    checks.append(_check("inventory: damaged_stock >= 0", bad_ds == 0,
                          f"{bad_ds} negative" if bad_ds else ""))

    # damaged_stock <= stock_received
    bad_dmg = (df["damaged_stock"] > df["stock_received"]).sum()
    checks.append(_check("inventory: damaged_stock <= stock_received", bad_dmg == 0,
                          f"{bad_dmg} rows where damaged > received (data quality issue in source)" if bad_dmg else ""))

    return df, _report("inventory", checks)


def clean_campaigns(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    checks = []
    df = df.copy()

    df["campaign_id"] = pd.to_numeric(df["campaign_id"], errors="coerce")
    for col in ["impressions", "clicks", "conversions", "spend",
                "revenue_generated", "roas"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["campaign_id", "campaign_name", "channel", "impressions",
                "clicks", "conversions", "spend", "revenue_generated", "roas"]:
        n = df[col].isna().sum()
        checks.append(_check(f"campaigns.{col} no nulls", n == 0,
                              f"{n} nulls" if n else ""))

    # Duplicate campaign_id
    dups = df["campaign_id"].duplicated().sum()
    checks.append(_check("campaigns: no duplicate campaign_id", dups == 0,
                          f"{dups} duplicates" if dups else ""))

    # Non-negative numerics
    for col in ["impressions", "clicks", "conversions", "spend", "revenue_generated"]:
        bad = (df[col] < 0).sum()
        checks.append(_check(f"campaigns: {col} >= 0", bad == 0,
                              f"{bad} negative" if bad else ""))

    # clicks <= impressions
    bad_ctr = (df["clicks"] > df["impressions"]).sum()
    checks.append(_check("campaigns: clicks <= impressions", bad_ctr == 0,
                          f"{bad_ctr} rows" if bad_ctr else ""))

    # channel values
    valid_ch = {"App", "Email", "SMS", "Social Media"}
    bad_ch = (~df["channel"].isin(valid_ch) & df["channel"].notna()).sum()
    checks.append(_check("campaigns: valid channel", bad_ch == 0,
                          f"{bad_ch} invalid" if bad_ch else ""))

    return df, _report("campaigns", checks)


def clean_products(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    checks = []
    df = df.copy()

    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    for col in ["price", "mrp", "margin_percentage", "shelf_life_days",
                "min_stock_level", "max_stock_level"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["product_id", "product_name", "category", "brand", "price", "mrp"]:
        n = df[col].isna().sum()
        checks.append(_check(f"products.{col} no nulls", n == 0,
                              f"{n} nulls" if n else ""))

    # Duplicate product_id
    dups = df["product_id"].duplicated().sum()
    checks.append(_check("products: no duplicate product_id", dups == 0,
                          f"{dups} duplicates" if dups else ""))

    # price > 0, mrp > 0
    for col in ["price", "mrp"]:
        bad = (df[col] <= 0).sum()
        checks.append(_check(f"products: {col} > 0", bad == 0,
                              f"{bad} non-positive" if bad else ""))

    # price <= mrp
    bad_margin = (df["price"] > df["mrp"]).sum()
    checks.append(_check("products: price <= mrp", bad_margin == 0,
                          f"{bad_margin} products where price > mrp" if bad_margin else ""))

    # min_stock <= max_stock
    bad_stock = (df["min_stock_level"] > df["max_stock_level"]).sum()
    checks.append(_check("products: min_stock_level <= max_stock_level", bad_stock == 0,
                          f"{bad_stock} rows" if bad_stock else ""))

    # Known categories
    valid_cats = {
        "Fruits & Vegetables", "Dairy & Breakfast", "Snacks & Munchies",
        "Cold Drinks & Juices", "Instant & Frozen Food", "Grocery & Staples",
        "Household Care", "Personal Care", "Baby Care", "Pet Care", "Pharmacy",
    }
    bad_cat = (~df["category"].isin(valid_cats) & df["category"].notna()).sum()
    checks.append(_check("products: valid category", bad_cat == 0,
                          f"{bad_cat} invalid" if bad_cat else ""))

    return df, _report("products", checks)


# ---------------------------------------------------------------------------
# Referential integrity checks
# ---------------------------------------------------------------------------

def check_referential_integrity(tables: dict[str, pd.DataFrame]) -> list[dict]:
    checks = []
    orders = tables.get("orders")
    feedback = tables.get("feedback")
    delivery = tables.get("delivery")
    customers = tables.get("customers")

    if orders is not None and feedback is not None:
        valid_oids = set(orders["order_id"].dropna())
        fb_oids = set(feedback["order_id"].dropna())
        orphans = fb_oids - valid_oids
        checks.append(_check(
            "referential: feedback.order_id -> orders",
            len(orphans) == 0,
            f"{len(orphans)} feedback order_ids not in orders table" if orphans else "",
        ))

    if orders is not None and delivery is not None:
        valid_oids = set(orders["order_id"].dropna())
        del_oids = set(delivery["order_id"].dropna())
        orphans = del_oids - valid_oids
        checks.append(_check(
            "referential: delivery.order_id -> orders",
            len(orphans) == 0,
            f"{len(orphans)} delivery order_ids not in orders table" if orphans else "",
        ))

    if customers is not None and orders is not None:
        valid_cids = set(customers["customer_id"].dropna())
        ord_cids = set(orders["customer_id"].dropna())
        orphans = ord_cids - valid_cids
        checks.append(_check(
            "referential: orders.customer_id -> customers",
            len(orphans) == 0,
            f"{len(orphans)} order customer_ids not in customers table" if orphans else "",
        ))

    return checks


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def load_tables(processed_dir: str = PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """Load processed CSVs from disk."""
    names = ["feedback", "customers", "delivery", "orders",
             "inventory", "campaigns", "products"]
    tables = {}
    for name in names:
        path = os.path.join(processed_dir, f"{name}.csv")
        if os.path.exists(path):
            tables[name] = pd.read_csv(path, low_memory=False)
        else:
            logger.warning("Processed file not found: %s", path)
    return tables


def run(processed_dir: str = PROCESSED_DIR) -> tuple[dict[str, pd.DataFrame], list[dict]]:
    """
    Load, clean, and validate all sub-tables.
    Returns (cleaned_tables, all_reports).
    """
    tables = load_tables(processed_dir)
    if not tables:
        raise RuntimeError(
            "No processed sub-tables found. Run data_splitting.py first."
        )

    cleaners = {
        "feedback": clean_feedback,
        "customers": clean_customers,
        "delivery": clean_delivery,
        "orders": clean_orders,
        "inventory": clean_inventory,
        "campaigns": clean_campaigns,
        "products": clean_products,
    }

    reports = []
    cleaned: dict[str, pd.DataFrame] = {}
    for name, cleaner in cleaners.items():
        if name not in tables:
            continue
        df_clean, report = cleaner(tables[name])
        cleaned[name] = df_clean
        reports.append(report)

    # Referential integrity
    ri_checks = check_referential_integrity(cleaned)
    reports.append({"table": "referential_integrity", "checks": ri_checks})

    # Save cleaned tables back to disk (overwrite)
    for name, df in cleaned.items():
        path = os.path.join(processed_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        logger.info("Saved cleaned %s (%d rows)", name, len(df))

    logger.info("Cleaning complete. %d tables processed.", len(cleaned))
    return cleaned, reports


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run()
