"""
visualization.py
================
Plotly chart builders.  Each function accepts pre-computed DataFrames
(from analysis.py) and returns a plotly Figure.

Design principles:
  - Clear titles, labelled axes, informative hover text.
  - Consistent color palette (qualitative, accessible).
  - No animations or excessive decoration.
"""

import pandas as pd
import visualization as viz
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Shared styling
# ---------------------------------------------------------------------------

COLORS = px.colors.qualitative.Set2
TEMPLATE = "plotly_white"
FONT_SIZE = 13


def _fig_layout(fig: go.Figure, title: str = "", **kwargs) -> go.Figure:
    fig.update_layout(
        template=TEMPLATE,
        title={"text": title, "font": {"size": 16}},
        font={"size": FONT_SIZE},
        margin={"l": 50, "r": 30, "t": 55, "b": 50},
        **kwargs,
    )
    return fig


# ---------------------------------------------------------------------------
# Orders & Revenue
# ---------------------------------------------------------------------------

def plot_revenue_trend(df: pd.DataFrame) -> go.Figure:
    """Line chart of monthly revenue and order count."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=df["period"], y=df["revenue"],
                   name="Revenue (₹)", line=dict(color=COLORS[0], width=2),
                   hovertemplate="Month: %{x|%b %Y}<br>Revenue: ₹%{y:,.0f}<extra></extra>"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(x=df["period"], y=df["num_orders"],
               name="# Orders", opacity=0.5,
               marker_color=COLORS[1],
               hovertemplate="Month: %{x|%b %Y}<br>Orders: %{y}<extra></extra>"),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="Revenue (₹)", secondary_y=False)
    fig.update_yaxes(title_text="Number of Orders", secondary_y=True)
    return _fig_layout(fig, "Monthly Revenue & Order Volume")


def plot_revenue_by_payment(df: pd.DataFrame) -> go.Figure:
    fig = px.pie(
        df, names="payment_method", values="revenue",
        color_discrete_sequence=COLORS,
        hole=0.4,
    )
    fig.update_traces(textinfo="percent+label",
                      hovertemplate="%{label}<br>Revenue: ₹%{value:,.0f}<br>Share: %{percent}<extra></extra>")
    return _fig_layout(fig, "Revenue by Payment Method")


def plot_revenue_by_store(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="store_id", y="revenue",
        color="revenue", color_continuous_scale="Blues",
        labels={"store_id": "Store ID", "revenue": "Revenue (₹)"},
        hover_data={"num_orders": True},
    )
    fig.update_coloraxes(showscale=False)
    return _fig_layout(fig, "Top Stores by Revenue")


def plot_order_value_distribution(df: pd.DataFrame) -> go.Figure:
    fig = px.histogram(
        df, x="order_total", nbins=50,
        color_discrete_sequence=[COLORS[2]],
        labels={"order_total": "Order Total (₹)", "count": "# Orders"},
    )
    fig.update_traces(hovertemplate="Order Total: ₹%{x:,.0f}<br>Count: %{y}<extra></extra>")
    return _fig_layout(fig, "Order Value Distribution")


def plot_revenue_by_category(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df.sort_values("revenue"), x="revenue", y="category",
        orientation="h",
        color="revenue", color_continuous_scale="Teal",
        labels={"revenue": "Revenue (₹)", "category": "Category"},
    )
    fig.update_coloraxes(showscale=False)
    return _fig_layout(fig, "Revenue by Product Category")


def plot_top_products(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df.sort_values("revenue"), x="revenue", y="product_name",
        orientation="h",
        color="category", color_discrete_sequence=COLORS,
        labels={"revenue": "Revenue (₹)", "product_name": "Product"},
        hover_data={"num_orders": True},
    )
    return _fig_layout(fig, "Top Products by Revenue")


# ---------------------------------------------------------------------------
# Delivery Performance
# ---------------------------------------------------------------------------

def plot_delivery_status(df: pd.DataFrame) -> go.Figure:
    color_map = {
        "On Time": "#2ecc71",
        "Slightly Delayed": "#f39c12",
        "Significantly Delayed": "#e74c3c",
    }
    colors = [color_map.get(s, "#95a5a6") for s in df["delivery_status"]]
    fig = px.pie(
        df, names="delivery_status", values="count",
        color="delivery_status", color_discrete_map=color_map,
        hole=0.4,
    )
    fig.update_traces(textinfo="percent+label",
                      hovertemplate="%{label}<br>Count: %{value:,}<br>Share: %{percent}<extra></extra>")
    return _fig_layout(fig, "Delivery Status Breakdown")


def plot_delay_reasons(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of delay reasons."""
    df = df.copy()
    df["reason"] = df["reason"].astype(str).str.strip()
    invalid_values = {"", "nan", "none", "n/a", "na", "null", "no delay", "on time"}
    df = df[~df["reason"].str.lower().isin(invalid_values)]

    # Force aggregation to exactly one row per reason
    df = df.groupby("reason", as_index=False)["count"].sum()
    df = df.sort_values("count")

    fig = go.Figure(go.Bar(
        x=df["count"], y=df["reason"],
        orientation="h",
        marker_color=COLORS[3],
        text=df["count"],
        texttemplate="%{text:,}",
        textposition="outside",
        hovertemplate="Reason: %{y}<br># Delayed Orders: %{x:,}<extra></extra>",
    ))
    
    # FIX: Limit bar thickness when there are very few categories
    if len(df) <= 2:
        fig.update_traces(width=0.3)

    max_count = df["count"].max() if len(df) else 1
    fig.update_xaxes(title="# Delayed Orders", range=[0, max_count * 1.25])
    fig.update_yaxes(title="Reason", type="category")
    return _fig_layout(fig, "Delay Reasons Breakdown")


def plot_delivery_time_dist(df: pd.DataFrame) -> go.Figure:
    fig = px.histogram(
        df, x="delivery_time_minutes", nbins=40,
        color_discrete_sequence=[COLORS[4]],
        labels={"delivery_time_minutes": "Delivery Time (min)", "count": "# Deliveries"},
    )
    return _fig_layout(fig, "Delivery Time Distribution (minutes)")


def plot_delay_vs_rating(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Avg Rating by Delivery Status",
                                        "Sentiment by Delivery Status"))
    status_order = ["On Time", "Slightly Delayed", "Significantly Delayed"]
    df_sorted = df.set_index("delivery_status").reindex(status_order).reset_index()
    colors_status = ["#2ecc71", "#f39c12", "#e74c3c"]

    fig.add_trace(
        go.Bar(x=df_sorted["delivery_status"], y=df_sorted["avg_rating"],
               marker_color=colors_status, showlegend=False,
               hovertemplate="Status: %{x}<br>Avg Rating: %{y:.2f}<extra></extra>"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(name="Positive %", x=df_sorted["delivery_status"],
               y=df_sorted["positive_pct"], marker_color="#2ecc71",
               hovertemplate="Status: %{x}<br>Positive: %{y:.1f}%<extra></extra>"),
        row=1, col=2,
    )
    fig.add_trace(
        go.Bar(name="Negative %", x=df_sorted["delivery_status"],
               y=df_sorted["negative_pct"], marker_color="#e74c3c",
               hovertemplate="Status: %{x}<br>Negative: %{y:.1f}%<extra></extra>"),
        row=1, col=2,
    )
    fig.update_yaxes(title_text="Avg Rating", row=1, col=1)
    fig.update_yaxes(title_text="Sentiment %", row=1, col=2)
    return _fig_layout(fig, "Delivery Delays vs Customer Satisfaction")


def plot_partner_performance(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df, x="avg_time", y="on_time_pct",
        size="total_deliveries", color="total_deliveries",
        color_continuous_scale="Viridis",
        labels={
            "avg_time": "Avg Delivery Time (min)",
            "on_time_pct": "On-Time %",
            "total_deliveries": "# Deliveries",
        },
        hover_data={"delivery_partner_id": True},
    )
    return _fig_layout(fig, "Delivery Partner Performance")


# ---------------------------------------------------------------------------
# Feedback & Ratings
# ---------------------------------------------------------------------------

def plot_rating_distribution(df: pd.DataFrame) -> go.Figure:
    star_colors = {1: "#e74c3c", 2: "#e67e22", 3: "#f1c40f",
                   4: "#2ecc71", 5: "#27ae60"}
    colors = [star_colors.get(int(r), "#95a5a6") for r in df["rating"]]
    fig = go.Figure(go.Bar(
        x=df["rating"].astype(str), y=df["count"],
        marker_color=colors,
        hovertemplate="Rating: %{x}⭐<br>Count: %{y:,}<extra></extra>",
    ))
    fig.update_xaxes(title="Rating")
    fig.update_yaxes(title="# Feedbacks")
    return _fig_layout(fig, "Rating Distribution")


def plot_sentiment_distribution(df: pd.DataFrame) -> go.Figure:
    color_map = {"Positive": "#2ecc71", "Neutral": "#f39c12", "Negative": "#e74c3c"}
    fig = px.pie(
        df, names="sentiment", values="count",
        color="sentiment", color_discrete_map=color_map,
        hole=0.4,
    )
    fig.update_traces(textinfo="percent+label",
                      hovertemplate="%{label}<br>Count: %{value:,}<extra></extra>")
    return _fig_layout(fig, "Sentiment Distribution")


def plot_rating_by_category(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df.sort_values("avg_rating"), x="avg_rating", y="feedback_category",
        orientation="h", color="avg_rating",
        color_continuous_scale=["#e74c3c", "#f1c40f", "#2ecc71"],
        range_color=[1, 5],
        labels={"avg_rating": "Avg Rating", "feedback_category": "Category"},
        hover_data={"count": True},
    )
    fig.update_coloraxes(showscale=False)
    return _fig_layout(fig, "Avg Rating by Feedback Category")


def plot_sentiment_over_time(df: pd.DataFrame) -> go.Figure:
    color_map = {"Positive": "#2ecc71", "Neutral": "#f39c12", "Negative": "#e74c3c"}
    fig = px.area(
        df, x="month", y="count", color="sentiment",
        color_discrete_map=color_map,
        labels={"month": "Month", "count": "# Feedbacks", "sentiment": "Sentiment"},
    )
    return _fig_layout(fig, "Sentiment Trend Over Time")


# ---------------------------------------------------------------------------
# Customer Analytics
# ---------------------------------------------------------------------------

def plot_customer_segments(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="customer_segment", y="count",
        color="customer_segment", color_discrete_sequence=COLORS,
        labels={"customer_segment": "Segment", "count": "# Customers"},
        hover_data={"avg_order_value": ":.2f", "avg_total_orders": ":.1f"},
    )
    return _fig_layout(fig, "Customer Segment Breakdown")


def plot_segment_revenue(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="customer_segment", y="revenue",
        color="customer_segment", color_discrete_sequence=COLORS,
        labels={"customer_segment": "Segment", "revenue": "Revenue (₹)"},
        hover_data={"num_orders": True},
    )
    return _fig_layout(fig, "Revenue by Customer Segment")


def plot_top_areas(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df.sort_values("count"), x="count", y="area",
        orientation="h",
        color="count", color_continuous_scale="Blues",
        labels={"count": "# Customers", "area": "Area"},
    )
    fig.update_coloraxes(showscale=False)
    return _fig_layout(fig, "Top Areas by Customer Count")


def plot_aov_by_segment(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="customer_segment", y="avg_order_value",
        color="customer_segment", color_discrete_sequence=COLORS,
        labels={"customer_segment": "Segment", "avg_order_value": "Avg Order Value (₹)"},
    )
    return _fig_layout(fig, "Avg Order Value by Customer Segment")


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def plot_stock_trend(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["total_received"],
        name="Stock Received", line=dict(color=COLORS[0], width=2),
        hovertemplate="Month: %{x|%b %Y}<br>Received: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["period"], y=df["total_damaged"],
        name="Damaged Stock", line=dict(color="#e74c3c", width=2),
        hovertemplate="Month: %{x|%b %Y}<br>Damaged: %{y:,}<extra></extra>",
    ))
    fig.update_xaxes(title="Month")
    fig.update_yaxes(title="Units")
    return _fig_layout(fig, "Stock Received vs Damaged Over Time")


def plot_damage_rate_by_category(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df.sort_values("damage_rate"), x="damage_rate", y="category",
        orientation="h",
        color="damage_rate", color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
        labels={"damage_rate": "Damage Rate (%)", "category": "Category"},
        hover_data={"total_received": True, "total_damaged": True},
    )
    fig.update_coloraxes(showscale=False)
    return _fig_layout(fig, "Stock Damage Rate by Category (%)")


def plot_damage_rate_products(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df.sort_values("damage_rate"), x="damage_rate", y="product_name",
        orientation="h",
        color="category", color_discrete_sequence=COLORS,
        labels={"damage_rate": "Damage Rate (%)", "product_name": "Product"},
    )
    return _fig_layout(fig, "Top Products by Damage Rate")


# ---------------------------------------------------------------------------
# Marketing & Campaigns
# ---------------------------------------------------------------------------

def plot_roas_by_channel(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("ROAS by Channel", "Spend vs Revenue by Channel"))
    colors_ch = {ch: COLORS[i] for i, ch in enumerate(df["channel"].unique())}

    fig.add_trace(
        go.Bar(x=df["channel"], y=df["roas"],
               marker_color=[colors_ch.get(c, "#95a5a6") for c in df["channel"]],
               showlegend=False,
               hovertemplate="Channel: %{x}<br>ROAS: %{y:.2f}x<extra></extra>"),
        row=1, col=1,
    )
    for ch in df["channel"]:
        row_d = df[df["channel"] == ch].iloc[0]
        fig.add_trace(
            go.Bar(name=ch, x=[ch], y=[row_d["spend"]],
                   marker_color=colors_ch.get(ch, "#95a5a6"),
                   showlegend=True,
                   hovertemplate=f"Channel: {ch}<br>Spend: ₹%{{y:,.0f}}<extra></extra>"),
            row=1, col=2,
        )
        fig.add_trace(
            go.Bar(name=f"{ch} Rev", x=[ch], y=[row_d["revenue"]],
                   marker_color=colors_ch.get(ch, "#95a5a6"),
                   opacity=0.5, showlegend=False,
                   hovertemplate=f"Channel: {ch}<br>Revenue: ₹%{{y:,.0f}}<extra></extra>"),
            row=1, col=2,
        )
    fig.update_yaxes(title_text="ROAS (x)", row=1, col=1)
    fig.update_yaxes(title_text="₹", row=1, col=2)
    return _fig_layout(fig, "Campaign Channel Performance", barmode="group")


def plot_spend_vs_revenue_scatter(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df, x="spend", y="revenue_generated",
        color="channel", size="roas",
        hover_name="campaign_name",
        color_discrete_sequence=COLORS,
        labels={"spend": "Ad Spend (₹)", "revenue_generated": "Revenue Generated (₹)",
                "roas": "ROAS"},
    )
    # Reference line y=x (break-even)
    max_val = max(df["spend"].max(), df["revenue_generated"].max())
    fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                  line=dict(dash="dash", color="gray"))
    return _fig_layout(fig, "Spend vs Revenue by Campaign (dashed = break-even)")


def plot_top_campaigns_roas(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    top = df.nlargest(top_n, "roas")
    bottom = df.nsmallest(top_n, "roas")
    combined = pd.concat([top, bottom]).drop_duplicates()
    fig = px.bar(
        combined.sort_values("roas"), x="roas", y="campaign_name",
        orientation="h",
        color="roas", color_continuous_scale=["#e74c3c", "#f1c40f", "#2ecc71"],
        labels={"roas": "ROAS", "campaign_name": "Campaign"},
    )
    fig.update_coloraxes(showscale=False)
    return _fig_layout(fig, "Best & Worst Campaigns by ROAS")


def plot_roas_by_audience(df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        df, x="target_audience", y="roas",
        color="target_audience", color_discrete_sequence=COLORS,
        labels={"target_audience": "Target Audience", "roas": "ROAS"},
    )
    return _fig_layout(fig, "ROAS by Target Audience")


def plot_ctr_conversion(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Click-Through Rate by Channel",
                                        "Conversion Rate by Channel"))
    colors_ch = {ch: COLORS[i] for i, ch in enumerate(df["channel"].unique())}
    fig.add_trace(
        go.Bar(x=df["channel"], y=df["ctr"],
               marker_color=[colors_ch.get(c, "#95a5a6") for c in df["channel"]],
               showlegend=False,
               hovertemplate="Channel: %{x}<br>CTR: %{y:.2f}%<extra></extra>"),
        row=1, col=1,
    )
    conv_by_ch = df.copy()
    conv_by_ch["conv_rate"] = conv_by_ch["conversions"] / conv_by_ch["clicks"] * 100
    fig.add_trace(
        go.Bar(x=conv_by_ch["channel"], y=conv_by_ch["conv_rate"],
               marker_color=[colors_ch.get(c, "#95a5a6") for c in conv_by_ch["channel"]],
               showlegend=False,
               hovertemplate="Channel: %{x}<br>Conv Rate: %{y:.2f}%<extra></extra>"),
        row=1, col=2,
    )
    fig.update_yaxes(title_text="CTR (%)", row=1, col=1)
    fig.update_yaxes(title_text="Conv. Rate (%)", row=1, col=2)
    return _fig_layout(fig, "CTR & Conversion Rate by Channel")

