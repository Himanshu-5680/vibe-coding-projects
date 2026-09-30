"""
analysis.py
===========
Business analytics across the 7 cleaned sub-tables.

All results are computed from the actual data — nothing is hardcoded.
Each public function returns a pandas DataFrame or a plain dict,
making them easy to call from both the dashboard and standalone scripts.
"""

import logging
import os

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.join("data", "processed")


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

def load_tables(processed_dir: str = PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """
    Load all cleaned sub-tables, casting date/numeric columns.
    Returns a dict of {table_name: DataFrame}.
    """
    tables = {}
    names = ["feedback", "customers", "delivery", "orders",
             "inventory", "campaigns", "products"]

    for name in names:
        path = os.path.join(processed_dir, f"{name}.csv")
        if not os.path.exists(path):
            logger.warning("Sub-table not found: %s", path)
            continue
        df = pd.read_csv(path, low_memory=False)
        tables[name] = df

    # Type casts
    if "orders" in tables:
        o = tables["orders"]
        for col in ["order_id", "customer_id", "product_id", "quantity",
                    "unit_price", "order_total", "store_id"]:
            o[col] = pd.to_numeric(o[col], errors="coerce")
        o["order_date"] = pd.to_datetime(o["order_date"], errors="coerce")
        o["actual_delivery_time"] = pd.to_datetime(o["actual_delivery_time"], errors="coerce")
        o["promised_delivery_time"] = pd.to_datetime(o["promised_delivery_time"], errors="coerce")

    if "feedback" in tables:
        f = tables["feedback"]
        for col in ["feedback_id", "order_id", "customer_id", "rating"]:
            f[col] = pd.to_numeric(f[col], errors="coerce")
        f["feedback_date"] = pd.to_datetime(f["feedback_date"], errors="coerce")

    if "customers" in tables:
        c = tables["customers"]
        for col in ["customer_id", "total_orders", "avg_order_value"]:
            c[col] = pd.to_numeric(c[col], errors="coerce")
        c["registration_date"] = pd.to_datetime(c["registration_date"], errors="coerce")

    if "delivery" in tables:
        d = tables["delivery"]
        for col in ["order_id", "delivery_partner_id",
                    "delivery_time_minutes", "distance_km"]:
            d[col] = pd.to_numeric(d[col], errors="coerce")
        d["promised_time"] = pd.to_datetime(d["promised_time"], errors="coerce")
        d["actual_time"] = pd.to_datetime(d["actual_time"], errors="coerce")

    if "inventory" in tables:
        inv = tables["inventory"]
        for col in ["product_id", "stock_received", "damaged_stock"]:
            inv[col] = pd.to_numeric(inv[col], errors="coerce")
        inv["date"] = pd.to_datetime(inv["date"], format="mixed",
                                      dayfirst=True, errors="coerce")

    if "campaigns" in tables:
        camp = tables["campaigns"]
        for col in ["campaign_id", "impressions", "clicks", "conversions",
                    "spend", "revenue_generated", "roas"]:
            camp[col] = pd.to_numeric(camp[col], errors="coerce")

    if "products" in tables:
        p = tables["products"]
        for col in ["product_id", "price", "mrp", "margin_percentage",
                    "shelf_life_days", "min_stock_level", "max_stock_level"]:
            p[col] = pd.to_numeric(p[col], errors="coerce")

    return tables


# ---------------------------------------------------------------------------
# KPI Overview
# ---------------------------------------------------------------------------

def overview_kpis(tables: dict) -> dict:
    """
    Returns a dict of top-level KPI values for the Overview tab.
    """
    kpis = {}

    orders = tables.get("orders")
    if orders is not None:
        kpis["total_orders"] = int(orders["order_id"].nunique())
        kpis["total_revenue"] = float(orders["order_total"].sum())
        kpis["avg_order_value"] = float(orders["order_total"].mean())

    feedback = tables.get("feedback")
    if feedback is not None:
        kpis["avg_rating"] = float(feedback["rating"].mean())

    delivery = tables.get("delivery")
    if delivery is not None:
        total = len(delivery)
        on_time = (delivery["delivery_status"] == "On Time").sum()
        kpis["on_time_pct"] = float(on_time / total * 100) if total else 0.0
        kpis["avg_delivery_minutes"] = float(delivery["delivery_time_minutes"].mean())

    campaigns = tables.get("campaigns")
    if campaigns is not None:
        kpis["total_ad_spend"] = float(campaigns["spend"].sum())
        
        # FIX: Multi-Touch Attribution Double-Counting
        # Marketing channels claim overlapping revenue. Use actual company revenue for true overall ROAS.
        if orders is not None and campaigns["spend"].sum() > 0:
            true_revenue = float(orders["order_total"].sum())
            kpis["overall_roas"] = float(true_revenue / campaigns["spend"].sum())
        else:
            kpis["overall_roas"] = 0.0

    return kpis
# ---------------------------------------------------------------------------
# Orders & Revenue
# ---------------------------------------------------------------------------

def revenue_over_time(orders: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """Monthly (or other freq) revenue trend."""
    o = orders.dropna(subset=["order_date", "order_total"]).copy()
    o["period"] = o["order_date"].dt.to_period(freq).dt.to_timestamp()
    return (
        o.groupby("period")
        .agg(revenue=("order_total", "sum"), num_orders=("order_id", "count"))
        .reset_index()
        .sort_values("period")
    )


def revenue_by_payment_method(orders: pd.DataFrame) -> pd.DataFrame:
    return (
        orders.dropna(subset=["payment_method", "order_total"])
        .groupby("payment_method")
        .agg(revenue=("order_total", "sum"), num_orders=("order_id", "count"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )


def revenue_by_store(orders: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    result = (
        orders.dropna(subset=["store_id", "order_total"])
        .groupby("store_id")
        .agg(revenue=("order_total", "sum"), num_orders=("order_id", "count"))
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(top_n)
    )
    result["store_id"] = result["store_id"].astype(int).astype(str)
    return result


def order_value_distribution(orders: pd.DataFrame) -> pd.DataFrame:
    """Returns order_total values for histogram plotting."""
    return orders[["order_total"]].dropna()


def top_products_by_revenue(orders: pd.DataFrame, products: pd.DataFrame,
                             top_n: int = 15) -> pd.DataFrame:
    o = orders.dropna(subset=["product_id", "order_total"]).copy()
    merged = o.merge(
        products[["product_id", "product_name", "category"]],
        on="product_id", how="left"
    )
    return (
        merged.groupby(["product_id", "product_name", "category"])
        .agg(revenue=("order_total", "sum"), num_orders=("order_id", "count"))
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(top_n)
    )


def revenue_by_category(orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    o = orders.dropna(subset=["product_id", "order_total"]).copy()
    merged = o.merge(
        products[["product_id", "category"]],
        on="product_id", how="left"
    )
    return (
        merged.dropna(subset=["category"])
        .groupby("category")
        .agg(revenue=("order_total", "sum"), num_orders=("order_id", "count"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )


# ---------------------------------------------------------------------------
# Delivery Performance
# ---------------------------------------------------------------------------

def delivery_status_breakdown(delivery: pd.DataFrame) -> pd.DataFrame:
    return (
        delivery.groupby("delivery_status")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )


def delay_reasons(delivery: pd.DataFrame) -> pd.DataFrame:
    delayed = delivery[delivery["delivery_status"] != "On Time"]
    return (
        delayed["reasons_if_delayed"]
        .dropna()
        .value_counts()
        .reset_index()
        .rename(columns={"reasons_if_delayed": "reason", "count": "count"})
    )


def delivery_time_distribution(delivery: pd.DataFrame) -> pd.DataFrame:
    return delivery[["delivery_time_minutes"]].dropna()


def delivery_by_partner(delivery: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    result = (
        delivery.groupby("delivery_partner_id")
        .agg(
            total_deliveries=("order_id", "count"),
            on_time=("delivery_status", lambda x: (x == "On Time").sum()),
            avg_time=("delivery_time_minutes", "mean"),
        )
        .reset_index()
    )
    result["on_time_pct"] = result["on_time"] / result["total_deliveries"] * 100
    result["delivery_partner_id"] = result["delivery_partner_id"].astype(int).astype(str)
    return result.sort_values("total_deliveries", ascending=False).head(top_n)


def delay_vs_rating(delivery: pd.DataFrame, feedback: pd.DataFrame) -> pd.DataFrame:
    """Join delivery status to feedback ratings to explore correlation."""
    del_sel = delivery[["order_id", "delivery_status", "delivery_time_minutes"]]
    fb_sel = feedback[["order_id", "rating", "sentiment"]]
    merged = del_sel.merge(fb_sel, on="order_id", how="inner")
    return (
        merged.groupby("delivery_status")
        .agg(
            avg_rating=("rating", "mean"),
            positive_pct=("sentiment", lambda x: (x == "Positive").mean() * 100),
            negative_pct=("sentiment", lambda x: (x == "Negative").mean() * 100),
            count=("order_id", "count"),
        )
        .reset_index()
    )


# ---------------------------------------------------------------------------
# Customer Feedback & Ratings
# ---------------------------------------------------------------------------

def avg_rating_by_category(feedback: pd.DataFrame) -> pd.DataFrame:
    return (
        feedback.groupby("feedback_category")
        .agg(avg_rating=("rating", "mean"), count=("feedback_id", "count"))
        .reset_index()
        .sort_values("avg_rating", ascending=False)
    )


def sentiment_distribution(feedback: pd.DataFrame) -> pd.DataFrame:
    return (
        feedback["sentiment"]
        .value_counts()
        .reset_index()
        .rename(columns={"sentiment": "sentiment", "count": "count"})
    )


def rating_distribution(feedback: pd.DataFrame) -> pd.DataFrame:
    return (
        feedback["rating"]
        .value_counts()
        .sort_index()
        .reset_index()
        .rename(columns={"rating": "rating", "count": "count"})
    )


def feedback_over_time(feedback: pd.DataFrame) -> pd.DataFrame:
    f = feedback.dropna(subset=["feedback_date"]).copy()
    f["month"] = f["feedback_date"].dt.to_period("M").dt.to_timestamp()
    return (
        f.groupby(["month", "sentiment"])
        .size()
        .reset_index(name="count")
        .sort_values("month")
    )


# ---------------------------------------------------------------------------
# Customer Analytics
# ---------------------------------------------------------------------------

def customer_segment_breakdown(customers: pd.DataFrame) -> pd.DataFrame:
    return (
        customers.groupby("customer_segment")
        .agg(count=("customer_id", "count"),
             avg_order_value=("avg_order_value", "mean"),
             avg_total_orders=("total_orders", "mean"))
        .reset_index()
    )


def top_areas_by_customers(customers: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    return (
        customers.groupby("area")
        .agg(count=("customer_id", "count"),
             avg_order_value=("avg_order_value", "mean"))
        .reset_index()
        .sort_values("count", ascending=False)
        .head(top_n)
    )


def customer_orders_joined(customers: pd.DataFrame,
                            orders: pd.DataFrame) -> pd.DataFrame:
    """Per-customer revenue summary."""
    ord_summary = (
        orders.groupby("customer_id")
        .agg(order_count=("order_id", "count"),
             total_spent=("order_total", "sum"))
        .reset_index()
    )
    return customers.merge(ord_summary, on="customer_id", how="left")


def segment_revenue(customers: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    merged = orders.merge(
        customers[["customer_id", "customer_segment"]], on="customer_id", how="left"
    )
    return (
        merged.dropna(subset=["customer_segment"])
        .groupby("customer_segment")
        .agg(revenue=("order_total", "sum"), num_orders=("order_id", "count"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )


# ---------------------------------------------------------------------------
# Inventory & Stock
# ---------------------------------------------------------------------------

def stock_trend(inventory: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    inv = inventory.dropna(subset=["date", "stock_received"]).copy()
    inv["period"] = inv["date"].dt.to_period(freq).dt.to_timestamp()
    return (
        inv.groupby("period")
        .agg(total_received=("stock_received", "sum"),
             total_damaged=("damaged_stock", "sum"))
        .reset_index()
        .sort_values("period")
    )


def damage_rate_by_product(inventory: pd.DataFrame,
                            products: pd.DataFrame, top_n: int = 15) -> pd.DataFrame:
    summary = (
        inventory.groupby("product_id")
        .agg(total_received=("stock_received", "sum"),
             total_damaged=("damaged_stock", "sum"))
        .reset_index()
    )
    summary["damage_rate"] = np.where(
        summary["total_received"] > 0,
        summary["total_damaged"] / summary["total_received"] * 100,
        0.0,
    )
    merged = summary.merge(
        products[["product_id", "product_name", "category"]], on="product_id", how="left"
    )
    return merged.sort_values("damage_rate", ascending=False).head(top_n)


def damage_rate_by_category(inventory: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    summary = (
        inventory.groupby("product_id")
        .agg(total_received=("stock_received", "sum"),
             total_damaged=("damaged_stock", "sum"))
        .reset_index()
    )
    merged = summary.merge(
        products[["product_id", "category"]], on="product_id", how="left"
    )
    return (
        merged.dropna(subset=["category"])
        .groupby("category")
        .agg(total_received=("total_received", "sum"),
             total_damaged=("total_damaged", "sum"))
        .assign(damage_rate=lambda x: x["total_damaged"] / x["total_received"] * 100)
        .reset_index()
        .sort_values("damage_rate", ascending=False)
    )


# ---------------------------------------------------------------------------
# Marketing Campaigns
# ---------------------------------------------------------------------------

def campaign_performance(campaigns: pd.DataFrame) -> pd.DataFrame:
    """Per-campaign: spend, revenue, ROAS, CTR, conversion rate."""
    c = campaigns.copy()
    c["ctr"] = np.where(c["impressions"] > 0,
                        c["clicks"] / c["impressions"] * 100, 0.0)
    c["conv_rate"] = np.where(c["clicks"] > 0,
                              c["conversions"] / c["clicks"] * 100, 0.0)
    return c.sort_values("roas", ascending=False)


def roas_by_channel(campaigns: pd.DataFrame) -> pd.DataFrame:
    return (
        campaigns.groupby("channel")
        .agg(spend=("spend", "sum"),
             revenue=("revenue_generated", "sum"),
             impressions=("impressions", "sum"),
             clicks=("clicks", "sum"),
             conversions=("conversions", "sum"))
        .assign(roas=lambda x: x["revenue"] / x["spend"])
        .assign(ctr=lambda x: x["clicks"] / x["impressions"] * 100)
        .reset_index()
        .sort_values("roas", ascending=False)
    )


def roas_by_audience(campaigns: pd.DataFrame) -> pd.DataFrame:
    return (
        campaigns.groupby("target_audience")
        .agg(spend=("spend", "sum"),
             revenue=("revenue_generated", "sum"))
        .assign(roas=lambda x: x["revenue"] / x["spend"])
        .reset_index()
        .sort_values("roas", ascending=False)
    )


def spend_vs_revenue(campaigns: pd.DataFrame) -> pd.DataFrame:
    return campaigns[["campaign_name", "channel", "spend",
                       "revenue_generated", "roas"]].copy()


# ---------------------------------------------------------------------------
# Product analytics
# ---------------------------------------------------------------------------

def top_products_by_volume(orders: pd.DataFrame, products: pd.DataFrame,
                            top_n: int = 15) -> pd.DataFrame:
    o = orders.dropna(subset=["product_id"]).copy()
    merged = o.merge(
        products[["product_id", "product_name", "category", "margin_percentage"]],
        on="product_id", how="left"
    )
    return (
        merged.groupby(["product_id", "product_name", "category"])
        .agg(total_quantity=("quantity", "sum"),
             total_revenue=("order_total", "sum"))
        .reset_index()
        .sort_values("total_quantity", ascending=False)
        .head(top_n)
    )


def margin_by_category(products: pd.DataFrame) -> pd.DataFrame:
    return (
        products.dropna(subset=["category", "margin_percentage"])
        .groupby("category")
        .agg(avg_margin=("margin_percentage", "mean"),
             product_count=("product_id", "count"))
        .reset_index()
        .sort_values("avg_margin", ascending=False)
    )


# ---------------------------------------------------------------------------
# Arithmetic consistency report (for display in dashboard)
# ---------------------------------------------------------------------------

def order_total_consistency(orders: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame flagging orders where
    quantity × unit_price != order_total (diff > 0.01).
    NOTE: mismatches are expected (taxes/fees/discounts) — just reported.
    """
    o = orders.dropna(subset=["quantity", "unit_price", "order_total"]).copy()
    o["calc_total"] = o["quantity"] * o["unit_price"]
    o["diff"] = (o["order_total"] - o["calc_total"]).round(2)
    o["pct_diff"] = (o["diff"] / o["order_total"] * 100).round(1)
    mismatch = o[abs(o["diff"]) > 0.01].copy()
    return mismatch[["order_id", "quantity", "unit_price",
                      "calc_total", "order_total", "diff", "pct_diff"]]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    tables = load_tables()
    kpis = overview_kpis(tables)
    print("KPIs:", kpis)
