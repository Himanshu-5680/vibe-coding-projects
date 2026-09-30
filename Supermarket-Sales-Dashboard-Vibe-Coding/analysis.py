"""
analysis.py — Core data loading, cleaning, and aggregation logic
for the Supermarket Sales Analysis project.
"""

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────
# 1. Load & Clean
# ─────────────────────────────────────────────

def load_data(filepath: str = "SUPER MARKET DATA.xlsx") -> pd.DataFrame:
    """Load the Excel dataset and return a cleaned DataFrame."""
    df = pd.read_excel(filepath, sheet_name=0)

    # ── Standardise column names ──────────────────────────────────────────
    df.columns = [c.strip() for c in df.columns]

    # ── Drop fully empty rows/cols ────────────────────────────────────────
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)

    # ── Parse dates ───────────────────────────────────────────────────────
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # ── Numeric coercion ─────────────────────────────────────────────────
    for col in ["Quantity", "Unit Price", "Rating", "Sales"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Fill / drop remaining missing values ─────────────────────────────
    # Drop rows where critical numeric columns are NaN
    critical = [c for c in ["Quantity", "Unit Price"] if c in df.columns]
    df.dropna(subset=critical, inplace=True)

    # Fill categorical NaNs with "Unknown"
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    df[cat_cols] = df[cat_cols].fillna("Unknown")

    # ── (Re)calculate Sales = Quantity × Unit Price ───────────────────────
    # If Sales column already exists we recalculate to ensure consistency
    df["Sales"] = df["Quantity"] * df["Unit Price"]

    # ── Strip whitespace from string columns ─────────────────────────────
    for col in cat_cols:
        df[col] = df[col].str.strip()

    # ── Derive time features ──────────────────────────────────────────────
    if "Date" in df.columns:
        df["Month"] = df["Date"].dt.to_period("M").astype(str)
        df["Day"] = df["Date"].dt.day_name()

    df.reset_index(drop=True, inplace=True)
    return df


# ─────────────────────────────────────────────
# 2. Summary Aggregations
# ─────────────────────────────────────────────

def summary_stats(df: pd.DataFrame) -> dict:
    """Return top-level KPI metrics."""
    return {
        "total_sales": df["Sales"].sum(),
        "total_transactions": len(df),
        "avg_sales_per_txn": df["Sales"].mean(),
        "avg_rating": df["Rating"].mean() if "Rating" in df.columns else None,
        "total_quantity": df["Quantity"].sum(),
    }


def sales_by_branch(df: pd.DataFrame) -> pd.DataFrame:
    """Total & average sales grouped by Branch."""
    return (
        df.groupby("Branch")
        .agg(
            Total_Sales=("Sales", "sum"),
            Avg_Sales=("Sales", "mean"),
            Transactions=("Sales", "count"),
            Avg_Rating=("Rating", "mean"),
        )
        .reset_index()
        .sort_values("Total_Sales", ascending=False)
    )


def sales_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Total sales grouped by product Category."""
    return (
        df.groupby("Category")
        .agg(Total_Sales=("Sales", "sum"), Transactions=("Sales", "count"))
        .reset_index()
        .sort_values("Total_Sales", ascending=False)
    )


def sales_by_product(df: pd.DataFrame) -> pd.DataFrame:
    """Top products by total sales."""
    return (
        df.groupby("Product")
        .agg(Total_Sales=("Sales", "sum"), Quantity_Sold=("Quantity", "sum"))
        .reset_index()
        .sort_values("Total_Sales", ascending=False)
    )


def sales_by_payment(df: pd.DataFrame) -> pd.DataFrame:
    """Transaction count and total sales by Payment method."""
    return (
        df.groupby("Payment")
        .agg(Total_Sales=("Sales", "sum"), Transactions=("Sales", "count"))
        .reset_index()
        .sort_values("Total_Sales", ascending=False)
    )


def sales_by_gender(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("Gender")
        .agg(Total_Sales=("Sales", "sum"), Transactions=("Sales", "count"))
        .reset_index()
    )


def sales_by_customer_type(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("Customer Type")
        .agg(Total_Sales=("Sales", "sum"), Transactions=("Sales", "count"))
        .reset_index()
    )


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly total sales trend."""
    return (
        df.groupby("Month")
        .agg(Total_Sales=("Sales", "sum"))
        .reset_index()
        .sort_values("Month")
    )


def top_products_by_branch(df: pd.DataFrame) -> pd.DataFrame:
    """Total sales per Product per Branch (for heatmap / grouped bar)."""
    return (
        df.groupby(["Branch", "Product"])["Sales"]
        .sum()
        .reset_index()
        .rename(columns={"Sales": "Total_Sales"})
    )
