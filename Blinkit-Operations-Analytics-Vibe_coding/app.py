"""
app.py
======
Blinkit Operations Analytics Dashboard
Streamlit entry point.

Run with:
    streamlit run app.py
"""

import os
import sys
import logging

import pandas as pd
import streamlit as st

os.chdir(os.path.abspath(os.path.dirname(__file__)))

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import analysis as ana
import visualization as viz

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Blinkit Operations Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Minimal custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
[data-testid="metric-container"] {
    background: #f7f8fa;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 12px 16px;
}
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #1f2328;
    margin-top: 8px;
    margin-bottom: 4px;
}
.insight-box {
    background: #f0f9ff;
    border-left: 4px solid #3b82d4;
    border-radius: 4px;
    padding: 10px 14px;
    margin-top: 8px;
    font-size: 0.9rem;
    color: black;
}
.warn-box {
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
    border-radius: 4px;
    padding: 10px 14px;
    margin-top: 8px;
    font-size: 0.9rem;
    color: black;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading data…")
def load_data() -> dict[str, pd.DataFrame]:
    return ana.load_tables()


@st.cache_data(show_spinner=False)
def load_icons() -> tuple[dict, dict]:
    """
    Load Category_Icons.xlsx and Rating_Icon.xlsx from data/raw.
    Returns (category_icon_map, rating_icon_map).
    On failure returns empty dicts — non-blocking.
    """
    cat_icons: dict = {}
    rat_icons: dict = {}
    try:
        cat_path = os.path.join("data", "raw", "Category_Icons.xlsx")
        if os.path.exists(cat_path):
            df_cat = pd.read_excel(cat_path)
            # Columns: category, Img
            if "category" in df_cat.columns and "Img" in df_cat.columns:
                cat_icons = dict(zip(df_cat["category"], df_cat["Img"]))
    except Exception as e:
        logger.warning("Could not load Category_Icons.xlsx: %s", e)

    try:
        rat_path = os.path.join("data", "raw", "Rating_Icon.xlsx")
        if os.path.exists(rat_path):
            df_rat = pd.read_excel(rat_path)
            # Columns: Rating, Emoji, Star
            if "Rating" in df_rat.columns and "Emoji" in df_rat.columns:
                rat_icons = dict(zip(df_rat["Rating"], df_rat["Emoji"]))
    except Exception as e:
        logger.warning("Could not load Rating_Icon.xlsx: %s", e)

    return cat_icons, rat_icons


def run_pipeline_if_needed():
    """Run data splitting + cleaning if processed files are missing."""
    processed_dir = os.path.join("data", "processed")
    marker = os.path.join(processed_dir, "orders.csv")
    if not os.path.exists(marker):
        with st.spinner("First run: splitting & cleaning data — this may take ~30 seconds…"):
            import data_splitting
            import data_cleaning
            tables_raw = data_splitting.run()
            data_cleaning.run()
        st.success("Data pipeline complete! Reload to start.")
        st.stop()


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

def sidebar_filters(tables: dict) -> dict:
    st.sidebar.header("🔍 Filters")
    filters: dict = {}

    orders = tables.get("orders")
    if orders is not None and "order_date" in orders.columns:
        o = orders.copy()
        o["order_date"] = pd.to_datetime(o["order_date"], errors="coerce")
        min_d = o["order_date"].min()
        max_d = o["order_date"].max()
        if pd.notna(min_d) and pd.notna(max_d):
            date_range = st.sidebar.date_input(
                "Order Date Range",
                value=(min_d.date(), max_d.date()),
                min_value=min_d.date(),
                max_value=max_d.date(),
            )
            if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                filters["date_start"] = pd.Timestamp(date_range[0])
                filters["date_end"] = pd.Timestamp(date_range[1])

    if orders is not None and "payment_method" in orders.columns:
        pm_options = sorted(orders["payment_method"].dropna().unique())
        selected_pm = st.sidebar.multiselect(
            "Payment Method", pm_options, default=pm_options
        )
        filters["payment_methods"] = selected_pm

    if orders is not None and "product_id" in orders.columns:
        products = tables.get("products")
        if products is not None and "category" in products.columns:
            cat_options = sorted(products["category"].dropna().unique())
            selected_cats = st.sidebar.multiselect(
                "Product Category", cat_options, default=cat_options
            )
            filters["categories"] = selected_cats

    customers = tables.get("customers")
    if customers is not None and "customer_segment" in customers.columns:
        seg_options = sorted(customers["customer_segment"].dropna().unique())
        selected_segs = st.sidebar.multiselect(
            "Customer Segment", seg_options, default=seg_options
        )
        filters["customer_segments"] = selected_segs

    campaigns = tables.get("campaigns")
    if campaigns is not None and "channel" in campaigns.columns:
        ch_options = sorted(campaigns["channel"].dropna().unique())
        selected_chs = st.sidebar.multiselect(
            "Campaign Channel", ch_options, default=ch_options
        )
        filters["channels"] = selected_chs

    return filters


# ---------------------------------------------------------------------------
# Filter application helpers
# ---------------------------------------------------------------------------

def filter_orders(orders: pd.DataFrame, filters: dict,
                   products: pd.DataFrame | None = None) -> pd.DataFrame:
    o = orders.copy()
    o["order_date"] = pd.to_datetime(o["order_date"], errors="coerce")

    if "date_start" in filters and "date_end" in filters:
        o = o[(o["order_date"] >= filters["date_start"]) &
              (o["order_date"] <= filters["date_end"])]
    if "payment_methods" in filters and filters["payment_methods"]:
        o = o[o["payment_method"].isin(filters["payment_methods"])]

    if "categories" in filters and filters["categories"] and products is not None:
        prod_ids = products[products["category"].isin(filters["categories"])]["product_id"]
        o = o[o["product_id"].isin(prod_ids)]

    return o


def filter_customers(customers: pd.DataFrame, filters: dict) -> pd.DataFrame:
    c = customers.copy()
    if "customer_segments" in filters and filters["customer_segments"]:
        c = c[c["customer_segment"].isin(filters["customer_segments"])]
    return c


def filter_campaigns(campaigns: pd.DataFrame, filters: dict) -> pd.DataFrame:
    c = campaigns.copy()
    if "channels" in filters and filters["channels"]:
        c = c[c["channel"].isin(filters["channels"])]
    return c


# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------

def kpi_card(col, label: str, value: str, delta: str | None = None):
    with col:
        st.metric(label=label, value=value, delta=delta)


# ---------------------------------------------------------------------------
# Tab: Overview
# ---------------------------------------------------------------------------

def tab_overview(tables: dict, filters: dict, cat_icons: dict, rat_icons: dict):
    st.subheader("📊 Dashboard Overview")
    st.markdown("Key performance indicators across all operational areas.")

    orders_f = filter_orders(
        tables["orders"], filters, tables.get("products")
    ) if "orders" in tables else pd.DataFrame()
    delivery = tables.get("delivery", pd.DataFrame())
    feedback_t = tables.get("feedback", pd.DataFrame())
    campaigns_f = filter_campaigns(
        tables["campaigns"], filters
    ) if "campaigns" in tables else pd.DataFrame()

    # KPI row 1
    c1, c2, c3, c4 = st.columns(4)
    total_orders = int(orders_f["order_id"].nunique()) if not orders_f.empty else 0
    total_rev = orders_f["order_total"].sum() if not orders_f.empty else 0
    avg_ov = orders_f["order_total"].mean() if not orders_f.empty else 0
    kpi_card(c1, "Total Orders", f"{total_orders:,}")
    kpi_card(c2, "Total Revenue", f"₹{total_rev:,.0f}")
    kpi_card(c3, "Avg Order Value", f"₹{avg_ov:,.0f}")

    avg_r = feedback_t["rating"].mean() if not feedback_t.empty else 0
    rating_label = "Avg Customer Rating"
    rat_icon = ""
    if rat_icons:
        rounded = int(round(avg_r))
        rat_icon = rat_icons.get(rounded, "")
    kpi_card(c4, rating_label, f"{avg_r:.2f} / 5")

    # KPI row 2
    c5, c6, c7, c8 = st.columns(4)
    if not delivery.empty:
        total_del = len(delivery)
        on_time = (delivery["delivery_status"] == "On Time").sum()
        ot_pct = on_time / total_del * 100 if total_del else 0
        avg_del = delivery["delivery_time_minutes"].mean()
    else:
        ot_pct = avg_del = 0

    total_spend = campaigns_f["spend"].sum() if not campaigns_f.empty else 0
    total_rev_camp = campaigns_f["revenue_generated"].sum() if not campaigns_f.empty else 0
    overall_roas = total_rev_camp / total_spend if total_spend > 0 else 0

    kpi_card(c5, "On-Time Delivery %", f"{ot_pct:.1f}%")
    kpi_card(c6, "Avg Delivery Time", f"{avg_del:.1f} min")
    kpi_card(c7, "Total Ad Spend", f"₹{total_spend:,.0f}")
    kpi_card(c8, "Overall ROAS", f"{overall_roas:.2f}x")

    st.divider()

    # Two summary charts side by side
    col_l, col_r = st.columns(2)
    with col_l:
        if not orders_f.empty:
            trend = ana.revenue_over_time(orders_f)
            if not trend.empty:
                st.plotly_chart(viz.plot_revenue_trend(trend),
                                use_container_width=True, key="ov_rev_trend")
    with col_r:
        if not delivery.empty:
            status_df = ana.delivery_status_breakdown(delivery)
            st.plotly_chart(viz.plot_delivery_status(status_df),
                            use_container_width=True, key="ov_del_status")

    # Business insights box
    st.markdown("#### 💡 Key Highlights")
    insights = []
    if not orders_f.empty:
        insights.append(f"**{total_orders:,} orders** recorded with a total revenue of "
                        f"**₹{total_rev:,.0f}** (avg order value ₹{avg_ov:,.0f}).")
    if not delivery.empty:
        insights.append(f"**{ot_pct:.1f}%** of deliveries were on time with an average "
                        f"delivery time of **{avg_del:.1f} minutes**.")
    if not feedback_t.empty:
        insights.append(f"Average customer rating: **{avg_r:.2f}/5**.")
    if not campaigns_f.empty:
        insights.append(f"Marketing ROAS: **{overall_roas:.2f}x** "
                        f"(₹{total_rev_camp:,.0f} revenue from ₹{total_spend:,.0f} spend).")
    for ins in insights:
        st.markdown(f'<div class="insight-box">{ins}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab: Orders & Revenue
# ---------------------------------------------------------------------------

def tab_orders(tables: dict, filters: dict):
    st.subheader("🛒 Orders & Revenue")
    if "orders" not in tables:
        st.warning("Orders data not available.")
        return

    orders_f = filter_orders(tables["orders"], filters, tables.get("products"))
    products = tables.get("products", pd.DataFrame())

    if orders_f.empty:
        st.info("No orders match the selected filters.")
        return

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Orders", f"{orders_f['order_id'].nunique():,}")
    kpi_card(c2, "Revenue", f"₹{orders_f['order_total'].sum():,.0f}")
    kpi_card(c3, "Avg Order Value", f"₹{orders_f['order_total'].mean():,.0f}")
    kpi_card(c4, "Unique Products", f"{orders_f['product_id'].nunique():,}")

    st.divider()

    # Revenue trend
    trend = ana.revenue_over_time(orders_f)
    if not trend.empty:
        st.plotly_chart(viz.plot_revenue_trend(trend),
                        use_container_width=True, key="ord_trend")

    col1, col2 = st.columns(2)
    with col1:
        pm_df = ana.revenue_by_payment_method(orders_f)
        st.plotly_chart(viz.plot_revenue_by_payment(pm_df),
                        use_container_width=True, key="ord_pm")
    with col2:
        ov_df = ana.order_value_distribution(orders_f)
        st.plotly_chart(viz.plot_order_value_distribution(ov_df),
                        use_container_width=True, key="ord_dist")

    # Revenue by category
    if not products.empty and "category" in products.columns:
        cat_df = ana.revenue_by_category(orders_f, products)
        if not cat_df.empty:
            st.plotly_chart(viz.plot_revenue_by_category(cat_df),
                            use_container_width=True, key="ord_cat")

    # Top stores
    store_df = ana.revenue_by_store(orders_f)
    if not store_df.empty:
        st.plotly_chart(viz.plot_revenue_by_store(store_df),
                        use_container_width=True, key="ord_store")

    # Top products
    if not products.empty:
        top_p = ana.top_products_by_revenue(orders_f, products)
        if not top_p.empty:
            st.plotly_chart(viz.plot_top_products(top_p),
                            use_container_width=True, key="ord_top_prod")

    # Data quality note
    consistency = ana.order_total_consistency(orders_f)
    st.markdown("#### ⚠️ Order Total Consistency Check")
    mismatch_count = len(consistency)
    total_checked = len(orders_f.dropna(subset=["quantity", "unit_price", "order_total"]))
    st.markdown(
        f'<div class="warn-box">'
        f'<strong>{mismatch_count:,} / {total_checked:,} orders</strong> have '
        f'<code>order_total ≠ quantity × unit_price</code>. '
        f'This is expected: <em>order_total</em> likely includes taxes, '
        f'delivery fees, or discounts not captured in the dataset. '
        f'Source values are preserved unchanged.</div>',
        unsafe_allow_html=True,
    )
    if mismatch_count > 0:
        with st.expander("View sample mismatches (first 20 rows)"):
            st.dataframe(consistency.head(20), use_container_width=True)


# ---------------------------------------------------------------------------
# Tab: Delivery Performance
# ---------------------------------------------------------------------------

def tab_delivery(tables: dict):
    st.subheader("🚚 Delivery Performance")
    delivery = tables.get("delivery")
    feedback = tables.get("feedback")
    if delivery is None or delivery.empty:
        st.warning("Delivery data not available.")
        return

    delivery = delivery.copy()
    delivery["delivery_time_minutes"] = pd.to_numeric(
        delivery["delivery_time_minutes"], errors="coerce"
    )

    c1, c2, c3, c4 = st.columns(4)
    total = len(delivery)
    on_time = (delivery["delivery_status"] == "On Time").sum()
    kpi_card(c1, "Total Deliveries", f"{total:,}")
    kpi_card(c2, "On Time", f"{on_time:,}")
    kpi_card(c3, "On-Time Rate", f"{on_time/total*100:.1f}%")
    kpi_card(c4, "Avg Delivery Time", f"{delivery['delivery_time_minutes'].mean():.1f} min")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        status_df = ana.delivery_status_breakdown(delivery)
        st.plotly_chart(viz.plot_delivery_status(status_df),
                        use_container_width=True, key="del_status")
    with col2:
        reason_df = ana.delay_reasons(delivery)
        if not reason_df.empty:
            st.plotly_chart(viz.plot_delay_reasons(reason_df),
                            use_container_width=True, key="del_reasons")

    col3, col4 = st.columns(2)
    with col3:
        dt_df = ana.delivery_time_distribution(delivery)
        st.plotly_chart(viz.plot_delivery_time_dist(dt_df),
                        use_container_width=True, key="del_time_dist")
    with col4:
        partner_df = ana.delivery_by_partner(delivery)
        if not partner_df.empty:
            st.plotly_chart(viz.plot_partner_performance(partner_df),
                            use_container_width=True, key="del_partner")

    # Delivery vs customer satisfaction
    if feedback is not None and not feedback.empty:
        feedback = feedback.copy()
        feedback["rating"] = pd.to_numeric(feedback["rating"], errors="coerce")
        dr_df = ana.delay_vs_rating(delivery, feedback)
        if not dr_df.empty:
            st.plotly_chart(viz.plot_delay_vs_rating(dr_df),
                            use_container_width=True, key="del_vs_rating")

    # Insights
    delayed = delivery[delivery["delivery_status"] != "On Time"]
    st.markdown("#### 💡 Delivery Insights")
    delay_pct = 100 - on_time / total * 100
    insight_txt = (
        f"**{delay_pct:.1f}%** of deliveries were delayed. "
        f"The most common delay reason is **"
        f"{reason_df['reason'].iloc[0] if (isinstance(reason_df, pd.DataFrame) and not reason_df.empty) else 'N/A'}"
        f"**. Average delivery time: **{delivery['delivery_time_minutes'].mean():.1f} min**."
    )
    st.markdown(f'<div class="insight-box">{insight_txt}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Tab: Customer Feedback & Ratings
# ---------------------------------------------------------------------------

def tab_feedback(tables: dict, rat_icons: dict):
    st.subheader("⭐ Customer Feedback & Ratings")
    feedback = tables.get("feedback")
    if feedback is None or feedback.empty:
        st.warning("Feedback data not available.")
        return

    feedback = feedback.copy()
    feedback["rating"] = pd.to_numeric(feedback["rating"], errors="coerce")
    feedback["feedback_date"] = pd.to_datetime(feedback["feedback_date"], errors="coerce")

    avg_r = feedback["rating"].mean()
    pos_pct = (feedback["sentiment"] == "Positive").mean() * 100
    neg_pct = (feedback["sentiment"] == "Negative").mean() * 100

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Total Feedbacks", f"{len(feedback):,}")
    kpi_card(c2, "Avg Rating", f"{avg_r:.2f} / 5")
    kpi_card(c3, "Positive Sentiment", f"{pos_pct:.1f}%")
    kpi_card(c4, "Negative Sentiment", f"{neg_pct:.1f}%")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        rd_df = ana.rating_distribution(feedback)
        st.plotly_chart(viz.plot_rating_distribution(rd_df),
                        use_container_width=True, key="fb_rating_dist")
    with col2:
        sent_df = ana.sentiment_distribution(feedback)
        st.plotly_chart(viz.plot_sentiment_distribution(sent_df),
                        use_container_width=True, key="fb_sentiment")

    col3, col4 = st.columns(2)
    with col3:
        cat_df = ana.avg_rating_by_category(feedback)
        st.plotly_chart(viz.plot_rating_by_category(cat_df),
                        use_container_width=True, key="fb_cat_rating")
    with col4:
        time_df = ana.feedback_over_time(feedback)
        if not time_df.empty:
            st.plotly_chart(viz.plot_sentiment_over_time(time_df),
                            use_container_width=True, key="fb_sent_time")

    # Rating breakdown table with icons
    st.markdown("#### Rating Breakdown")
    rd_df_display = rd_df.copy()
    if rat_icons:
        rd_df_display["Stars"] = rd_df_display["rating"].apply(
            lambda r: rat_icons.get(int(r), str(r))
        )
        rd_df_display = rd_df_display.rename(columns={"rating": "Rating", "count": "Count"})
        st.dataframe(rd_df_display[["Stars", "Rating", "Count"]],
                     use_container_width=False, hide_index=True)
    else:
        st.dataframe(rd_df_display, use_container_width=False, hide_index=True)


# ---------------------------------------------------------------------------
# Tab: Marketing & Campaigns
# ---------------------------------------------------------------------------

def tab_marketing(tables: dict, filters: dict):
    st.subheader("📣 Marketing Campaigns")
    campaigns = tables.get("campaigns")
    if campaigns is None or campaigns.empty:
        st.warning("Campaigns data not available.")
        return

    campaigns_f = filter_campaigns(campaigns, filters)
    if campaigns_f.empty:
        st.info("No campaigns match the selected filters.")
        return

    for col in ["impressions", "clicks", "conversions", "spend",
                "revenue_generated", "roas"]:
        campaigns_f[col] = pd.to_numeric(campaigns_f[col], errors="coerce")

    total_spend = campaigns_f["spend"].sum()
    total_rev = campaigns_f["revenue_generated"].sum()
    roas = total_rev / total_spend if total_spend > 0 else 0
    avg_ctr = (campaigns_f["clicks"].sum() / campaigns_f["impressions"].sum() * 100
               if campaigns_f["impressions"].sum() > 0 else 0)

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Total Campaigns", f"{campaigns_f['campaign_id'].nunique():,}")
    kpi_card(c2, "Total Spend", f"₹{total_spend:,.0f}")
    kpi_card(c3, "Revenue Generated", f"₹{total_rev:,.0f}")
    kpi_card(c4, "Overall ROAS", f"{roas:.2f}x")

    st.divider()

    # ROAS by channel
    ch_df = ana.roas_by_channel(campaigns_f)
    st.plotly_chart(viz.plot_roas_by_channel(ch_df),
                    use_container_width=True, key="mkt_roas_ch")

    col1, col2 = st.columns(2)
    with col1:
        # CTR & Conversion
        st.plotly_chart(viz.plot_ctr_conversion(ch_df),
                        use_container_width=True, key="mkt_ctr")
    with col2:
        # ROAS by audience
        aud_df = ana.roas_by_audience(campaigns_f)
        st.plotly_chart(viz.plot_roas_by_audience(aud_df),
                        use_container_width=True, key="mkt_aud")

    # Spend vs Revenue scatter
    sv_df = ana.spend_vs_revenue(campaigns_f)
    st.plotly_chart(viz.plot_spend_vs_revenue_scatter(sv_df),
                    use_container_width=True, key="mkt_scatter")

    # Best/worst campaigns
    perf_df = ana.campaign_performance(campaigns_f)
    st.plotly_chart(viz.plot_top_campaigns_roas(perf_df),
                    use_container_width=True, key="mkt_top_camp")

    # Insights
    best_ch = ch_df.iloc[0]["channel"] if not ch_df.empty else "N/A"
    worst_ch = ch_df.iloc[-1]["channel"] if not ch_df.empty else "N/A"
    best_roas = ch_df.iloc[0]["roas"] if not ch_df.empty else 0
    st.markdown("#### 💡 Marketing Insights")
    st.markdown(
        f'<div class="insight-box">'
        f'Best-performing channel: <strong>{best_ch}</strong> (ROAS {best_roas:.2f}x). '
        f'Worst-performing channel: <strong>{worst_ch}</strong>. '
        f'Overall ROAS: <strong>{roas:.2f}x</strong> across all campaigns.</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tab: Inventory & Stock
# ---------------------------------------------------------------------------

def tab_inventory(tables: dict, filters: dict, cat_icons: dict):
    st.subheader("📦 Inventory & Stock")
    inventory = tables.get("inventory")
    products = tables.get("products")
    if inventory is None or inventory.empty:
        st.warning("Inventory data not available.")
        return

    inventory = inventory.copy()
    for col in ["stock_received", "damaged_stock"]:
        inventory[col] = pd.to_numeric(inventory[col], errors="coerce")
    inventory["date"] = pd.to_datetime(
        inventory["date"], format="mixed", dayfirst=True, errors="coerce"
    )

    # Filter by category if applicable
    if products is not None and "categories" in filters and filters["categories"]:
        prod_ids = products[products["category"].isin(filters["categories"])]["product_id"]
        inventory = inventory[inventory["product_id"].isin(prod_ids)]

    total_rec = inventory["stock_received"].sum()
    total_dmg = inventory["damaged_stock"].sum()
    dmg_rate = total_dmg / total_rec * 100 if total_rec > 0 else 0

    c1, c2, c3 = st.columns(3)
    kpi_card(c1, "Total Stock Received", f"{total_rec:,.0f}")
    kpi_card(c2, "Total Damaged Stock", f"{total_dmg:,.0f}")
    kpi_card(c3, "Overall Damage Rate", f"{dmg_rate:.1f}%")

    st.divider()

    # Stock trend over time
    trend = ana.stock_trend(inventory)
    if not trend.empty:
        st.plotly_chart(viz.plot_stock_trend(trend),
                        use_container_width=True, key="inv_trend")

    col1, col2 = st.columns(2)
    with col1:
        if products is not None:
            cat_dmg = ana.damage_rate_by_category(inventory, products)
            if not cat_dmg.empty:
                # Add category icon next to name if available
                if cat_icons:
                    cat_dmg["category_display"] = cat_dmg["category"].apply(
                        lambda c: c  # icons are URLs, displayed via st.image separately
                    )
                st.plotly_chart(viz.plot_damage_rate_by_category(cat_dmg),
                                use_container_width=True, key="inv_cat_dmg")
    with col2:
        if products is not None:
            prod_dmg = ana.damage_rate_by_product(inventory, products)
            if not prod_dmg.empty:
                st.plotly_chart(viz.plot_damage_rate_products(prod_dmg),
                                use_container_width=True, key="inv_prod_dmg")

    # Data quality warning
    bad_dmg = int((inventory["damaged_stock"] > inventory["stock_received"]).sum())
    if bad_dmg > 0:
        st.markdown(
            f'<div class="warn-box">'
            f'⚠️ <strong>{bad_dmg:,} inventory records</strong> have '
            f'<em>damaged_stock > stock_received</em>. '
            f'This is a data quality issue in the source data and has not been corrected.</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Tab: Customers
# ---------------------------------------------------------------------------

def tab_customers(tables: dict, filters: dict):
    st.subheader("👥 Customers")
    customers = tables.get("customers")
    orders = tables.get("orders")
    if customers is None or customers.empty:
        st.warning("Customer data not available.")
        return

    customers_f = filter_customers(customers, filters)
    for col in ["customer_id", "total_orders", "avg_order_value"]:
        customers_f[col] = pd.to_numeric(customers_f[col], errors="coerce")

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Total Customers", f"{len(customers_f):,}")
    kpi_card(c2, "Avg Total Orders", f"{customers_f['total_orders'].mean():.1f}")
    kpi_card(c3, "Avg Order Value", f"₹{customers_f['avg_order_value'].mean():,.0f}")
    kpi_card(c4, "Unique Areas", f"{customers_f['area'].nunique():,}")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        seg_df = ana.customer_segment_breakdown(customers_f)
        st.plotly_chart(viz.plot_customer_segments(seg_df),
                        use_container_width=True, key="cust_seg")
    with col2:
        st.plotly_chart(viz.plot_aov_by_segment(seg_df),
                        use_container_width=True, key="cust_aov")

    # Area chart
    area_df = ana.top_areas_by_customers(customers_f)
    st.plotly_chart(viz.plot_top_areas(area_df),
                    use_container_width=True, key="cust_area")

    # Segment revenue (needs orders)
    if orders is not None and not orders.empty:
        orders_f = filter_orders(orders, filters, tables.get("products"))
        for col_n in ["customer_id", "order_total"]:
            orders_f[col_n] = pd.to_numeric(orders_f[col_n], errors="coerce")
        seg_rev = ana.segment_revenue(customers_f, orders_f)
        if not seg_rev.empty:
            st.plotly_chart(viz.plot_segment_revenue(seg_rev),
                            use_container_width=True, key="cust_seg_rev")

    # Insights
    top_seg = customers_f.groupby("customer_segment")["customer_id"].count().idxmax()
    st.markdown("#### 💡 Customer Insights")
    st.markdown(
        f'<div class="insight-box">'
        f'Largest customer segment: <strong>{top_seg}</strong>. '
        f'Avg order value across all segments: '
        f'<strong>₹{customers_f["avg_order_value"].mean():,.0f}</strong>.</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tab: Generate Report
# ---------------------------------------------------------------------------

def tab_report(tables: dict):
    st.subheader("📄 Generate Report")
    st.markdown(
        "Generate a complete PowerPoint (.pptx) business report summarising all dashboard findings "
        "— suitable for sharing with non-technical stakeholders."
    )
    st.divider()

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.markdown("""
**What's included in the report:**
- Title slide with dataset scope
- Table of contents
- Dataset overview (7 sub-tables, row counts, descriptions)
- Data cleaning steps and quality issues
- Key Performance Indicators (8 headline numbers)
- Orders & Revenue analysis
- Delivery Performance analysis
- Customer Feedback & Ratings
- Marketing Campaigns (spend, ROAS, channels)
- Inventory & Stock (damage rates)
- Customer segment breakdown
- 7 key business insights (tied to real numbers)
- 6 concrete recommendations
        """)

    with col_btn:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        generate_clicked = st.button("📊 Generate Final Report", type="primary", use_container_width=True)

    if generate_clicked:
        try:
            with st.spinner("Building your PowerPoint report — this takes a few seconds…"):
                import report_generator as rg
                pptx_bytes = rg.generate_report(tables)

            st.success("Report generated successfully! Click below to download.")

            st.download_button(
                label="⬇️  Download Blinkit_Operations_Report.pptx",
                data=pptx_bytes,
                file_name="Blinkit_Operations_Report.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )

            st.markdown(
                '<div class="insight-box">'
                'The report contains <strong>13 slides</strong> with all figures '
                'calculated live from the dataset — nothing is hardcoded. '
                'Open the downloaded file in Microsoft PowerPoint or Google Slides.'
                '</div>',
                unsafe_allow_html=True,
            )

        except ImportError:
            st.error(
                "python-pptx is not installed. Run: `pip install python-pptx` then restart the app."
            )
        except Exception as e:
            st.error(f"Report generation failed: {e}")
            st.exception(e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    run_pipeline_if_needed()

    tables = load_data()
    if not tables:
        st.error("No processed data found. Please ensure data/processed/ contains the sub-table CSVs.")
        st.info("Run: `python src/data_splitting.py` then `python src/data_cleaning.py`")
        st.stop()

    cat_icons, rat_icons = load_icons()

    filters = sidebar_filters(tables)

    st.title("🛒 Blinkit Operations Analytics")
    st.markdown(
        "_Internship data analytics project — all insights are derived "
        "from `happy_merged.csv`._"
    )

    tabs = st.tabs([
        "📊 Overview",
        "🛒 Orders & Revenue",
        "🚚 Delivery",
        "⭐ Feedback & Ratings",
        "📣 Marketing",
        "📦 Inventory",
        "👥 Customers",
        "📄 Generate Report",
    ])

    with tabs[0]:
        tab_overview(tables, filters, cat_icons, rat_icons)
    with tabs[1]:
        tab_orders(tables, filters)
    with tabs[2]:
        tab_delivery(tables)
    with tabs[3]:
        tab_feedback(tables, rat_icons)
    with tabs[4]:
        tab_marketing(tables, filters)
    with tabs[5]:
        tab_inventory(tables, filters, cat_icons)
    with tabs[6]:
        tab_customers(tables, filters)
    with tabs[7]:
        tab_report(tables)


if __name__ == "__main__":
    main()
