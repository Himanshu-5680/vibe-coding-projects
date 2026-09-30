"""
app.py — Streamlit Dark-Theme Dashboard for Supermarket Sales Analysis
Run: streamlit run app.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from analysis import (
    load_data,
    summary_stats,
    sales_by_branch,
    sales_by_category,
    sales_by_product,
    sales_by_payment,
    sales_by_gender,
    sales_by_customer_type,
    monthly_trend,
    top_products_by_branch,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Supermarket Sales Analytics",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS — enforce dark theme, override Streamlit defaults
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Root / body ── */
    html, body, [data-testid="stAppViewContainer"],
    [data-testid="stMain"], .main, .block-container {
        background-color: #0d0f14 !important;
        color: #e8eaf0 !important;
    }
    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #12151e !important;
    }
    [data-testid="stSidebar"] * {
        color: #c9cdd8 !important;
    }
    /* ── Headers ── */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    /* ── Generic text ── */
    p, span, label, div {
        color: #d0d4e0 !important;
    }
    /* ── Metric cards ── */
    [data-testid="metric-container"] {
        background: #181c27 !important;
        border: 1px solid #2a3050 !important;
        border-radius: 10px !important;
        padding: 14px 18px !important;
    }
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #8b95b0 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.04em !important;
    }
    [data-testid="stMetricDelta"] {
        color: #7ec8e3 !important;
    }
    /* ── Tabs ── */
    [data-testid="stTabs"] button {
        color: #8b95b0 !important;
        background: transparent !important;
        border-bottom: 2px solid transparent !important;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #7eb3f5 !important;
        border-bottom: 2px solid #4a7fd4 !important;
    }
    /* ── DataFrames / tables ── */
    .dataframe, [data-testid="stDataFrame"] {
        background-color: #181c27 !important;
        color: #e0e4f0 !important;
    }
    /* ── Selectbox / multiselect ── */
    [data-testid="stSelectbox"] > div,
    [data-testid="stMultiSelect"] > div {
        background-color: #1e2335 !important;
        color: #e0e4f0 !important;
    }
    /* ── Dividers ── */
    hr { border-color: #2a3050 !important; }
    /* ── Section header pill ── */
    .section-pill {
        display: inline-block;
        background: #1a2340;
        border-left: 3px solid #4a7fd4;
        padding: 4px 14px;
        border-radius: 4px;
        color: #7eb3f5 !important;
        font-size: 0.88rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    /* ── Insight cards ── */
    .insight-card {
        background: #151a28;
        border: 1px solid #2a3a5c;
        border-left: 4px solid #4a7fd4;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        color: #d4daf0 !important;
    }
    .insight-card strong { color: #7eb3f5 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY DARK TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────
CHART_BG = "#0d0f14"
PAPER_BG = "#0d0f14"
GRID_COLOR = "#1e2335"
TEXT_COLOR = "#c9cdd8"
AXIS_COLOR = "#4a5270"

# Base layout — intentionally excludes xaxis/yaxis to avoid keyword collision
# when callers also pass xaxis_title / yaxis_title to update_layout().
PLOTLY_LAYOUT = dict(
    plot_bgcolor=CHART_BG,
    paper_bgcolor=PAPER_BG,
    font=dict(color=TEXT_COLOR, family="Segoe UI, Arial, sans-serif", size=12),
    legend=dict(
        bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_COLOR),
    ),
    margin=dict(l=40, r=20, t=50, b=40),
    colorway=["#4a7fd4", "#7ec8e3", "#a78bfa", "#34d399", "#fb923c",
              "#f472b6", "#facc15", "#60a5fa"],
)

# Axis styling applied separately via update_xaxes / update_yaxes
_AXIS_STYLE = dict(
    gridcolor=GRID_COLOR,
    zerolinecolor=GRID_COLOR,
    tickfont=dict(color=TEXT_COLOR),
    title_font=dict(color=TEXT_COLOR),
    linecolor=AXIS_COLOR,
)

COLOR_BRANCH = {"A": "#4a7fd4", "B": "#7ec8e3", "C": "#a78bfa"}
COLOR_SEQ = px.colors.sequential.Blues_r


def apply_layout(fig: go.Figure, title: str = "",
                 xaxis_title: str = "", yaxis_title: str = "") -> go.Figure:
    """Apply the standard dark layout to any Plotly figure."""
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font=dict(color="#ffffff", size=15)),
    )
    fig.update_xaxes(**_AXIS_STYLE, title_text=xaxis_title)
    fig.update_yaxes(**_AXIS_STYLE, title_text=yaxis_title)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING  (cached)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Loading dataset…")
def get_data():
    return load_data("Vibe_coding_Projects/Supermarket-Sales-Dashboard-Vibe-Coding/SUPER MARKET DATA.xlsx")


df_full = get_data()

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛒 Supermarket Analytics")
    st.markdown("---")
    st.markdown("### Filters")

    branches = sorted(df_full["Branch"].dropna().unique().tolist())
    sel_branch = st.multiselect("Branch", branches, default=branches)

    categories = sorted(df_full["Category"].dropna().unique().tolist())
    sel_cat = st.multiselect("Category", categories, default=categories)

    genders = sorted(df_full["Gender"].dropna().unique().tolist())
    sel_gender = st.multiselect("Gender", genders, default=genders)

    cust_types = sorted(df_full["Customer Type"].dropna().unique().tolist())
    sel_ctype = st.multiselect("Customer Type", cust_types, default=cust_types)

    st.markdown("---")
    st.markdown(
        "<span style='color:#8b95b0;font-size:0.78rem;'>500 transactions · "
        "SUPER MARKET DATA.xlsx</span>",
        unsafe_allow_html=True,
    )

# Apply filters
df = df_full[
    df_full["Branch"].isin(sel_branch)
    & df_full["Category"].isin(sel_cat)
    & df_full["Gender"].isin(sel_gender)
    & df_full["Customer Type"].isin(sel_ctype)
].copy()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN TITLE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='color:#ffffff;margin-bottom:4px;'>🛒 Supermarket Sales Dashboard</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='color:#8b95b0;margin-top:0;'>Data-driven insights from 500 supermarket transactions</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────────────────────
stats = summary_stats(df)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("💰 Total Sales", f"₹{stats['total_sales']:,.0f}")
k2.metric("🧾 Transactions", f"{stats['total_transactions']:,}")
k3.metric("📊 Avg Sale / Txn", f"₹{stats['avg_sales_per_txn']:,.1f}")
k4.metric("⭐ Avg Rating", f"{stats['avg_rating']:.2f}" if stats["avg_rating"] else "N/A")
k5.metric("📦 Units Sold", f"{int(stats['total_quantity']):,}")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏪 Branch Performance",
    "📦 Product & Category",
    "💳 Payment & Gender",
    "📅 Time Trends",
    "🔥 Product × Branch",
    "💡 Key Insights",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — BRANCH PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-pill">Branch Performance Overview</div>', unsafe_allow_html=True)

    branch_df = sales_by_branch(df)

    col_a, col_b = st.columns(2)

    with col_a:
        fig = go.Figure(
            go.Bar(
                x=branch_df["Branch"],
                y=branch_df["Total_Sales"],
                marker_color=[COLOR_BRANCH.get(b, "#4a7fd4") for b in branch_df["Branch"]],
                text=[f"₹{v:,.0f}" for v in branch_df["Total_Sales"]],
                textposition="outside",
                textfont=dict(color=TEXT_COLOR),
            )
        )
        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Total Sales by Branch", font=dict(color="#ffffff", size=15)),
        )
        fig.update_xaxes(**_AXIS_STYLE, title_text="Branch")
        fig.update_yaxes(**_AXIS_STYLE, title_text="Total Sales (₹)")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig2 = go.Figure(
            go.Bar(
                x=branch_df["Branch"],
                y=branch_df["Avg_Rating"],
                marker_color=["#7ec8e3", "#a78bfa", "#34d399"],
                text=[f"{v:.2f}" for v in branch_df["Avg_Rating"]],
                textposition="outside",
                textfont=dict(color=TEXT_COLOR),
            )
        )
        fig2.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Average Customer Rating by Branch", font=dict(color="#ffffff", size=15)),
        )
        fig2.update_xaxes(**_AXIS_STYLE, title_text="Branch")
        fig2.update_yaxes(**_AXIS_STYLE, title_text="Avg Rating", range=[0, 10])
        st.plotly_chart(fig2, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        fig3 = go.Figure(
            go.Bar(
                x=branch_df["Branch"],
                y=branch_df["Transactions"],
                marker_color=["#fb923c", "#facc15", "#f472b6"],
                text=branch_df["Transactions"],
                textposition="outside",
                textfont=dict(color=TEXT_COLOR),
            )
        )
        fig3.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Transaction Count by Branch", font=dict(color="#ffffff", size=15)),
        )
        fig3.update_xaxes(**_AXIS_STYLE, title_text="Branch")
        fig3.update_yaxes(**_AXIS_STYLE, title_text="No. of Transactions")
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        fig4 = go.Figure(
            go.Bar(
                x=branch_df["Branch"],
                y=branch_df["Avg_Sales"],
                marker_color=["#60a5fa", "#818cf8", "#34d399"],
                text=[f"₹{v:,.1f}" for v in branch_df["Avg_Sales"]],
                textposition="outside",
                textfont=dict(color=TEXT_COLOR),
            )
        )
        fig4.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Average Sales per Transaction by Branch", font=dict(color="#ffffff", size=15)),
        )
        fig4.update_xaxes(**_AXIS_STYLE, title_text="Branch")
        fig4.update_yaxes(**_AXIS_STYLE, title_text="Avg Sales (₹)")
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("#### Branch Summary Table")
    st.dataframe(
        branch_df.style.format({
            "Total_Sales": "₹{:,.1f}",
            "Avg_Sales": "₹{:,.1f}",
            "Avg_Rating": "{:.2f}",
        }),
        use_container_width=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — PRODUCT & CATEGORY
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-pill">Product & Category Analysis</div>', unsafe_allow_html=True)

    cat_df = sales_by_category(df)
    prod_df = sales_by_product(df)

    col_a, col_b = st.columns(2)

    with col_a:
        fig = px.pie(
            cat_df,
            names="Category",
            values="Total_Sales",
            hole=0.45,
            color_discrete_sequence=["#4a7fd4", "#7ec8e3", "#a78bfa", "#34d399",
                                      "#fb923c", "#f472b6", "#facc15"],
        )
        fig.update_traces(
            textfont=dict(color="#ffffff"),
            hovertemplate="<b>%{label}</b><br>Sales: ₹%{value:,.0f}<br>Share: %{percent}",
        )
        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Sales Share by Category", font=dict(color="#ffffff", size=15)),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig2 = go.Figure(
            go.Bar(
                x=cat_df["Total_Sales"],
                y=cat_df["Category"],
                orientation="h",
                marker=dict(
                    color=cat_df["Total_Sales"],
                    colorscale="Blues",
                    showscale=False,
                ),
                text=[f"₹{v:,.0f}" for v in cat_df["Total_Sales"]],
                textposition="outside",
                textfont=dict(color=TEXT_COLOR),
            )
        )
        fig2.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Total Sales by Category", font=dict(color="#ffffff", size=15)),
        )
        fig2.update_xaxes(**_AXIS_STYLE, title_text="Total Sales (₹)")
        fig2.update_yaxes(**_AXIS_STYLE, title_text="")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-pill">Top Products by Sales Revenue</div>', unsafe_allow_html=True)

    top_n = st.slider("Show top N products", min_value=5, max_value=min(30, len(prod_df)), value=10, step=1)
    top_prod = prod_df.head(top_n)

    fig3 = go.Figure(
        go.Bar(
            x=top_prod["Product"],
            y=top_prod["Total_Sales"],
            marker=dict(
                color=top_prod["Total_Sales"],
                colorscale="Blues",
                showscale=False,
            ),
            text=[f"₹{v:,.0f}" for v in top_prod["Total_Sales"]],
            textposition="outside",
            textfont=dict(color=TEXT_COLOR),
        )
    )
    fig3.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=f"Top {top_n} Products by Total Sales", font=dict(color="#ffffff", size=15)),
    )
    fig3.update_xaxes(**_AXIS_STYLE, title_text="Product", tickangle=-35)
    fig3.update_yaxes(**_AXIS_STYLE, title_text="Total Sales (₹)")
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = go.Figure(
        go.Bar(
            x=top_prod["Product"],
            y=top_prod["Quantity_Sold"],
            marker=dict(
                color=top_prod["Quantity_Sold"],
                colorscale="Teal",
                showscale=False,
            ),
            text=top_prod["Quantity_Sold"].astype(int),
            textposition="outside",
            textfont=dict(color=TEXT_COLOR),
        )
    )
    fig4.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=f"Top {top_n} Products by Quantity Sold", font=dict(color="#ffffff", size=15)),
    )
    fig4.update_xaxes(**_AXIS_STYLE, title_text="Product", tickangle=-35)
    fig4.update_yaxes(**_AXIS_STYLE, title_text="Quantity Sold")
    st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — PAYMENT & GENDER
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-pill">Payment Methods & Customer Demographics</div>', unsafe_allow_html=True)

    pay_df = sales_by_payment(df)
    gen_df = sales_by_gender(df)
    ctype_df = sales_by_customer_type(df)

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        fig = px.pie(
            pay_df,
            names="Payment",
            values="Total_Sales",
            hole=0.40,
            color_discrete_sequence=["#4a7fd4", "#7ec8e3", "#a78bfa", "#34d399"],
        )
        fig.update_traces(
            textfont=dict(color="#ffffff"),
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f} (%{percent})",
        )
        fig.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Sales by Payment Method", font=dict(color="#ffffff", size=14)),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig2 = px.pie(
            gen_df,
            names="Gender",
            values="Total_Sales",
            hole=0.40,
            color_discrete_sequence=["#60a5fa", "#f472b6"],
        )
        fig2.update_traces(
            textfont=dict(color="#ffffff"),
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f} (%{percent})",
        )
        fig2.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Sales by Gender", font=dict(color="#ffffff", size=14)),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_c:
        fig3 = px.pie(
            ctype_df,
            names="Customer Type",
            values="Total_Sales",
            hole=0.40,
            color_discrete_sequence=["#fb923c", "#a78bfa"],
        )
        fig3.update_traces(
            textfont=dict(color="#ffffff"),
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f} (%{percent})",
        )
        fig3.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Sales by Customer Type", font=dict(color="#ffffff", size=14)),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Payment × Branch grouped bar
    pay_branch = (
        df.groupby(["Branch", "Payment"])["Sales"].sum().reset_index()
    )
    fig4 = px.bar(
        pay_branch,
        x="Branch",
        y="Sales",
        color="Payment",
        barmode="group",
        color_discrete_sequence=["#4a7fd4", "#7ec8e3", "#a78bfa", "#34d399"],
        text_auto=True,
    )
    fig4.update_traces(textfont=dict(color="#ffffff"))
    fig4.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Payment Method Breakdown by Branch", font=dict(color="#ffffff", size=15)),
    )
    fig4.update_xaxes(**_AXIS_STYLE, title_text="Branch")
    fig4.update_yaxes(**_AXIS_STYLE, title_text="Total Sales (₹)")
    st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — TIME TRENDS
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-pill">Sales Trends Over Time</div>', unsafe_allow_html=True)

    monthly_df = monthly_trend(df)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_df["Month"],
        y=monthly_df["Total_Sales"],
        mode="lines+markers",
        line=dict(color="#4a7fd4", width=2.5),
        marker=dict(size=7, color="#7eb3f5"),
        fill="tozeroy",
        fillcolor="rgba(74,127,212,0.15)",
        hovertemplate="Month: %{x}<br>Sales: ₹%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Monthly Sales Trend", font=dict(color="#ffffff", size=15)),
    )
    fig.update_xaxes(**_AXIS_STYLE, title_text="Month")
    fig.update_yaxes(**_AXIS_STYLE, title_text="Total Sales (₹)")
    st.plotly_chart(fig, use_container_width=True)

    # Branch monthly trend
    branch_monthly = (
        df.groupby(["Month", "Branch"])["Sales"].sum().reset_index()
    )
    fig2 = px.line(
        branch_monthly,
        x="Month",
        y="Sales",
        color="Branch",
        markers=True,
        color_discrete_map=COLOR_BRANCH,
    )
    fig2.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Monthly Sales Trend by Branch", font=dict(color="#ffffff", size=15)),
    )
    fig2.update_xaxes(**_AXIS_STYLE, title_text="Month")
    fig2.update_yaxes(**_AXIS_STYLE, title_text="Total Sales (₹)")
    st.plotly_chart(fig2, use_container_width=True)

    # Day-of-week
    if "Day" in df.columns:
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_df = (
            df.groupby("Day")["Sales"].sum()
            .reindex([d for d in dow_order if d in df["Day"].unique()])
            .reset_index()
        )
        fig3 = go.Figure(go.Bar(
            x=dow_df["Day"],
            y=dow_df["Sales"],
            marker=dict(color=dow_df["Sales"], colorscale="Blues", showscale=False),
            text=[f"₹{v:,.0f}" for v in dow_df["Sales"]],
            textposition="outside",
            textfont=dict(color=TEXT_COLOR),
        ))
        fig3.update_layout(
            **PLOTLY_LAYOUT,
            title=dict(text="Total Sales by Day of Week", font=dict(color="#ffffff", size=15)),
        )
        fig3.update_xaxes(**_AXIS_STYLE, title_text="Day")
        fig3.update_yaxes(**_AXIS_STYLE, title_text="Total Sales (₹)")
        st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — PRODUCT × BRANCH HEATMAP
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    st.markdown('<div class="section-pill">Product Performance Across Branches</div>', unsafe_allow_html=True)

    pb_df = top_products_by_branch(df)

    # Pivot for heatmap
    pivot = pb_df.pivot(index="Product", columns="Branch", values="Total_Sales").fillna(0)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Blues",
        hoverongaps=False,
        hovertemplate="Branch: %{x}<br>Product: %{y}<br>Sales: ₹%{z:,.0f}<extra></extra>",
        colorbar=dict(
            tickfont=dict(color=TEXT_COLOR),
            title=dict(text="₹ Sales", font=dict(color=TEXT_COLOR)),
        ),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Sales Heatmap: Product × Branch", font=dict(color="#ffffff", size=15)),
        height=max(400, len(pivot) * 26),
    )
    fig.update_xaxes(**_AXIS_STYLE, title_text="Branch")
    fig.update_yaxes(**_AXIS_STYLE, title_text="Product")
    st.plotly_chart(fig, use_container_width=True)

    # Top 10 products grouped bar per branch
    top10_prods = prod_df = sales_by_product(df).head(10)["Product"].tolist()
    pb_top = pb_df[pb_df["Product"].isin(top10_prods)]

    fig2 = px.bar(
        pb_top,
        x="Product",
        y="Total_Sales",
        color="Branch",
        barmode="group",
        color_discrete_map=COLOR_BRANCH,
        text_auto=True,
    )
    fig2.update_traces(textfont=dict(color="#ffffff"))
    fig2.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Top 10 Products: Sales by Branch", font=dict(color="#ffffff", size=15)),
    )
    fig2.update_xaxes(**_AXIS_STYLE, title_text="Product", tickangle=-30)
    fig2.update_yaxes(**_AXIS_STYLE, title_text="Total Sales (₹)")
    st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — KEY INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────
with tab6:
    st.markdown('<div class="section-pill">Business Insights & Recommendations</div>', unsafe_allow_html=True)
    st.markdown("")

    branch_df = sales_by_branch(df)
    cat_df = sales_by_category(df)
    prod_df = sales_by_product(df)
    pay_df = sales_by_payment(df)
    gen_df = sales_by_gender(df)
    ctype_df = sales_by_customer_type(df)

    best_branch = branch_df.iloc[0]["Branch"] if not branch_df.empty else "N/A"
    best_branch_sales = branch_df.iloc[0]["Total_Sales"] if not branch_df.empty else 0
    best_cat = cat_df.iloc[0]["Category"] if not cat_df.empty else "N/A"
    best_cat_sales = cat_df.iloc[0]["Total_Sales"] if not cat_df.empty else 0
    best_prod = prod_df.iloc[0]["Product"] if not prod_df.empty else "N/A"
    best_pay = pay_df.iloc[0]["Payment"] if not pay_df.empty else "N/A"
    top_gender = gen_df.sort_values("Total_Sales", ascending=False).iloc[0]["Gender"] if not gen_df.empty else "N/A"
    top_ctype = ctype_df.sort_values("Total_Sales", ascending=False).iloc[0]["Customer Type"] if not ctype_df.empty else "N/A"
    avg_rating_branch = branch_df.sort_values("Avg_Rating", ascending=False).iloc[0]["Branch"] if not branch_df.empty else "N/A"

    insights = [
        (
            "🏆 Top Performing Branch",
            f"Branch <strong>{best_branch}</strong> leads with total sales of "
            f"<strong>₹{best_branch_sales:,.0f}</strong>. "
            "Focus additional marketing and staffing resources here to capitalise on existing momentum.",
        ),
        (
            "📦 Highest Revenue Category",
            f"<strong>{best_cat}</strong> is the top revenue-generating category at "
            f"<strong>₹{best_cat_sales:,.0f}</strong>. "
            "Ensure consistent stock availability and consider premium placement in-store.",
        ),
        (
            "🥇 Best-Selling Product",
            f"<strong>{best_prod}</strong> ranks #1 in revenue. "
            "Bundle promotions around this product to increase average basket size.",
        ),
        (
            "💳 Dominant Payment Method",
            f"<strong>{best_pay}</strong> is the most-used payment channel. "
            "Ensure seamless checkout experience and consider cashback promotions via this channel.",
        ),
        (
            "👤 Key Customer Segment",
            f"<strong>{top_gender}</strong> shoppers contribute the most to sales revenue. "
            f"<strong>{top_ctype}</strong> customers represent the highest-value segment — "
            "prioritise loyalty rewards for this group.",
        ),
        (
            "⭐ Customer Satisfaction",
            f"Branch <strong>{avg_rating_branch}</strong> achieves the highest average customer rating. "
            "Replicate its service and operational practices at underperforming branches.",
        ),
        (
            "📈 Growth Opportunity",
            "Categories with low transaction counts but reasonable average sales values represent "
            "high-margin upsell opportunities. Consider targeted promotions and staff training for these segments.",
        ),
        (
            "🗓️ Seasonal Strategy",
            "Review the Monthly Trend tab to identify peak sales months. "
            "Plan inventory restocking, staffing surges, and promotional campaigns 4–6 weeks before peak periods.",
        ),
    ]

    col_a, col_b = st.columns(2)
    for i, (title, body) in enumerate(insights):
        target_col = col_a if i % 2 == 0 else col_b
        with target_col:
            st.markdown(
                f'<div class="insight-card"><strong style="font-size:1rem;">{title}</strong>'
                f'<p style="margin-top:6px;color:#b0b8d0;">{body}</p></div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown('<div class="section-pill">Raw Data Explorer</div>', unsafe_allow_html=True)

    search_term = st.text_input("🔍 Search product or branch", "")
    display_df = df.copy()
    if search_term:
        mask = (
            display_df["Product"].str.contains(search_term, case=False, na=False)
            | display_df["Branch"].str.contains(search_term, case=False, na=False)
            | display_df["Category"].str.contains(search_term, case=False, na=False)
        )
        display_df = display_df[mask]

    st.dataframe(
        display_df[[
            "Invoice ID", "Date", "Branch", "City", "Customer Type",
            "Gender", "Product", "Category", "Quantity", "Unit Price",
            "Sales", "Payment", "Rating",
        ]].style.format({
            "Unit Price": "₹{:.2f}",
            "Sales": "₹{:.2f}",
            "Rating": "{:.1f}",
        }),
        use_container_width=True,
        height=350,
    )

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#4a5270;font-size:0.78rem;'>"
    "Supermarket Sales Analytics Dashboard · Built with Streamlit & Plotly · "
    "Dataset: SUPER MARKET DATA.xlsx"
    "</p>",
    unsafe_allow_html=True,
)
