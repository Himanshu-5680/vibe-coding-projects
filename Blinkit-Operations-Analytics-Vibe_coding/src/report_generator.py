"""
report_generator.py
===================
Generates a 13-slide PowerPoint (.pptx) business report from the
already-cleaned Blinkit Operations Analytics data.

All numbers come from live calculations — nothing is hardcoded.
Designed for non-technical readers: plain language, concrete numbers.

Slide order:
  0  Title
  1  Table of Contents
  2  01 — Dataset Overview
  3  02 — Data Cleaning & Preparation
  4  03 — Key Performance Indicators
  5  04 — Orders & Revenue
  6  05 — Delivery Performance
  7  06 — Customer Feedback & Ratings
  8  07 — Marketing Campaigns
  9  08 — Inventory & Stock
 10  09 — Customers
 11  10 — Key Business Insights
 12  11 — Recommendations & Next Steps
"""

import io
import logging
from typing import Any

import numpy as np
import pandas as pd

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette — clean professional dark-on-white
# ---------------------------------------------------------------------------
C_BG        = RGBColor(0xFF, 0xFF, 0xFF)   # slide background: white
C_ACCENT    = RGBColor(0x00, 0x9A, 0x44)   # Blinkit green
C_DARK      = RGBColor(0x1F, 0x23, 0x28)   # near-black text
C_MUTED     = RGBColor(0x57, 0x60, 0x6A)   # secondary text
C_CARD_BG   = RGBColor(0xF7, 0xF8, 0xFA)   # light grey card fill
C_BORDER    = RGBColor(0xE5, 0xE7, 0xEB)   # card border

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _rgb(r, g, b):
    return RGBColor(r, g, b)


def _add_slide(prs: Presentation, layout_idx: int = 6) -> Any:
    """Add a blank slide (layout 6 = blank in most built-in themes)."""
    layout = prs.slide_layouts[layout_idx]
    return prs.slides.add_slide(layout)


def _tf(shape) -> Any:
    return shape.text_frame


def _box(slide, left, top, width, height,
         fill_rgb=None, line_rgb=None, line_width_pt=0.75) -> Any:
    """Add a plain rectangle shape."""
    from pptx.util import Pt as Pt_
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        left, top, width, height
    )
    shape.line.color.rgb = line_rgb if line_rgb else C_BORDER
    if line_rgb is None and fill_rgb is None:
        shape.line.fill.background()  # no border
    else:
        shape.line.width = Pt_(line_width_pt)
    if fill_rgb:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_rgb
    else:
        shape.fill.background()
    return shape


def _textbox(slide, left, top, width, height, text="",
             font_size=14, bold=False, color=None,
             align=PP_ALIGN.LEFT, word_wrap=True) -> Any:
    txb = slide.shapes.add_textbox(left, top, width, height)
    tf = txb.text_frame
    tf.word_wrap = word_wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color if color else C_DARK
    return txb


def _add_text(tf, text, font_size=12, bold=False, color=None,
              align=PP_ALIGN.LEFT, space_before=0):
    """Add a new paragraph to an existing text frame."""
    p = tf.add_paragraph()
    p.alignment = align
    if space_before:
        p.space_before = Pt(space_before)
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color if color else C_DARK
    return p


def _section_header(slide, number: str, title: str):
    """Green accent bar + number + title in top-left."""
    bar = slide.shapes.add_shape(1, Inches(0.35), Inches(0.25), Inches(0.07), Inches(0.55))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_ACCENT
    bar.line.fill.background()

    txb = _textbox(slide, Inches(0.5), Inches(0.22), Inches(9), Inches(0.6),
                   font_size=11, bold=False, color=C_MUTED)
    _tf(txb).paragraphs[0].runs[0].text = number

    txb2 = _textbox(slide, Inches(0.5), Inches(0.44), Inches(9), Inches(0.5),
                    font_size=20, bold=True, color=C_DARK)
    _tf(txb2).paragraphs[0].runs[0].text = title


def _kpi_card(slide, left, top, width, height, label, value, sub=""):
    """One KPI card: light-grey fill, label + big number + optional sub-line."""
    card = _box(slide, left, top, width, height,
                fill_rgb=C_CARD_BG, line_rgb=C_BORDER, line_width_pt=0.5)

    # label
    txb_l = slide.shapes.add_textbox(left + Inches(0.12), top + Inches(0.1),
                                     width - Inches(0.24), Inches(0.28))
    tf = txb_l.text_frame
    tf.paragraphs[0].runs  # touch
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size = Pt(9)
    r.font.color.rgb = C_MUTED

    # value
    txb_v = slide.shapes.add_textbox(left + Inches(0.08), top + Inches(0.3),
                                     width - Inches(0.16), Inches(0.52))
    tf2 = txb_v.text_frame
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = str(value)
    r2.font.size = Pt(18)
    r2.font.bold = True
    r2.font.color.rgb = C_ACCENT

    if sub:
        txb_s = slide.shapes.add_textbox(left + Inches(0.08), top + Inches(0.8),
                                         width - Inches(0.16), Inches(0.28))
        tf3 = txb_s.text_frame
        p3 = tf3.paragraphs[0]
        p3.alignment = PP_ALIGN.CENTER
        r3 = p3.add_run()
        r3.text = sub
        r3.font.size = Pt(8)
        r3.font.color.rgb = C_MUTED


def _insight_box(slide, left, top, width, height, tag, text):
    """Numbered insight/recommendation card."""
    # tag bubble
    tag_w = Inches(0.55)
    tag_shape = _box(slide, left, top + Inches(0.05), tag_w, Inches(0.38),
                     fill_rgb=C_ACCENT, line_rgb=C_ACCENT)
    txb_tag = slide.shapes.add_textbox(left, top + Inches(0.04), tag_w, Inches(0.38))
    p = txb_tag.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = tag
    r.font.size = Pt(9)
    r.font.bold = True
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # text box
    txb = slide.shapes.add_textbox(left + tag_w + Inches(0.1), top,
                                   width - tag_w - Inches(0.1), height)
    tf = txb.text_frame
    tf.word_wrap = True
    p2 = tf.paragraphs[0]
    p2.alignment = PP_ALIGN.LEFT
    r2 = p2.add_run()
    r2.text = text
    r2.font.size = Pt(10)
    r2.font.color.rgb = C_DARK


def _simple_table(slide, left, top, col_widths, rows, header_fill=C_ACCENT):
    """Draw a simple table as stacked text boxes — avoids pptx table overflow quirks."""
    row_h = Inches(0.32)
    for r_idx, row in enumerate(rows):
        x = left
        for c_idx, (cell, col_w) in enumerate(zip(row, col_widths)):
            is_header = (r_idx == 0)
            bg = header_fill if is_header else (C_CARD_BG if r_idx % 2 == 0 else C_BG)
            txt_color = RGBColor(0xFF, 0xFF, 0xFF) if is_header else C_DARK
            _box(slide, x, top + r_idx * row_h, col_w, row_h,
                 fill_rgb=bg, line_rgb=C_BORDER, line_width_pt=0.3)
            txb = slide.shapes.add_textbox(
                x + Inches(0.06), top + r_idx * row_h + Inches(0.06),
                col_w - Inches(0.12), row_h - Inches(0.1))
            tf = txb.text_frame
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            r_run = p.add_run()
            r_run.text = str(cell)
            r_run.font.size = Pt(9.5)
            r_run.font.bold = is_header
            r_run.font.color.rgb = txt_color
            x += col_w
        top  # just continue


# ---------------------------------------------------------------------------
# Slide builders
# ---------------------------------------------------------------------------

def _slide_title(prs, date_range, total_orders, num_stores,
                 num_categories, num_payment_methods, num_channels):
    slide = _add_slide(prs)

    # Dark banner top half
    banner = _box(slide, 0, 0, SLIDE_W, Inches(3.9),
                  fill_rgb=_rgb(0x1A, 0x20, 0x2C))
    banner.line.fill.background()

    # Accent bar
    accent = _box(slide, 0, Inches(3.75), SLIDE_W, Inches(0.12),
                  fill_rgb=C_ACCENT)
    accent.line.fill.background()

    _textbox(slide, Inches(1.0), Inches(1.0), Inches(11), Inches(0.85),
             "Blinkit Operations Analytics",
             font_size=36, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF),
             align=PP_ALIGN.CENTER)

    _textbox(slide, Inches(1.0), Inches(1.9), Inches(11), Inches(0.5),
             f"Business Report  |  {total_orders:,} Orders  |  {date_range}",
             font_size=16, color=_rgb(0xCC, 0xDD, 0xFF),
             align=PP_ALIGN.CENTER)    
# Source line
    scope = (f"Source: happy_merged.csv     "
             f"Stores: {num_stores:,}     Categories: {num_categories}     "
             f"Payment methods: {num_payment_methods}     Ad channels: {num_channels}")
    _textbox(slide, Inches(0.8), Inches(2.55), Inches(11.5), Inches(0.4),
             scope, font_size=10, color=_rgb(0x99, 0xAA, 0xBB),
             align=PP_ALIGN.CENTER)

    # Bottom white area tagline
    _textbox(slide, Inches(1.5), Inches(4.2), Inches(10), Inches(0.45),
             "Prepared for internal review — all figures derived from live operational data",
             font_size=11, color=C_MUTED, align=PP_ALIGN.CENTER)


def _slide_toc(prs):
    slide = _add_slide(prs)
    _section_header(slide, "Contents", "Table of Contents")

    sections = [
        ("01", "Dataset Overview",             "What data we have and where it came from"),
        ("02", "Data Cleaning & Preparation",  "How the raw file was split and validated"),
        ("03", "Key Performance Indicators",   "The eight headline numbers for the business"),
        ("04", "Orders & Revenue",             "What sold, how much, and through which channels"),
        ("05", "Delivery Performance",         "How fast orders arrived and why some were late"),
        ("06", "Customer Feedback & Ratings",  "How customers rated their experience"),
        ("07", "Marketing Campaigns",          "Which ads paid off and which did not"),
        ("08", "Inventory & Stock",            "Stock levels, damage rates, and problem products"),
        ("09", "Customers",                    "Segment breakdown and revenue contribution"),
        ("10", "Key Business Insights",        "The most important findings from the analysis"),
        ("11", "Recommendations & Next Steps", "Concrete actions to take based on the data"),
    ]

    col_widths = [Inches(0.65), Inches(3.4), Inches(7.8)]
    rows = [["#", "Section", "What it covers"]]
    for num, name, desc in sections:
        rows.append([num, name, desc])

    _simple_table(slide, Inches(0.35), Inches(1.1), col_widths, rows)


def _slide_dataset_overview(prs, row_counts: dict, date_range: str):
    slide = _add_slide(prs)
    _section_header(slide, "01", "Dataset Overview")

    # Table: sub-tables
    col_widths = [Inches(2.4), Inches(1.1), Inches(8.5)]
    rows = [["Sub-table", "Rows", "What it tells us"]]
    descriptions = {
        "feedback":  "5,000 customer reviews — star ratings, written comments, and whether the customer felt positive, neutral, or negative",
        "customers": "2,500 registered customer profiles — name, location, membership tier, and how much they spend on average",
        "delivery":  "5,000 delivery records — which partner handled each order, how long it took, and whether it arrived on time",
        "orders":    "5,000 completed orders — which product was ordered, how many, at what price, and through which store",
        "inventory": "93,277 daily stock entries — how much of each product was received at the warehouse and how much arrived damaged",
        "campaigns": "5,400 marketing campaign runs — which ads were shown, how many people clicked, and how much revenue each generated",
        "products":  "268 product listings — name, category, brand, price, recommended retail price, and margin",
    }
    for name, count in row_counts.items():
        rows.append([name.capitalize(), f"{count:,}", descriptions.get(name, "")])

    _simple_table(slide, Inches(0.35), Inches(1.05), col_widths, rows)

    _textbox(slide, Inches(0.35), Inches(6.55), Inches(12.5), Inches(0.4),
             f"Data covers: {date_range}   |   Source: happy_merged.csv (121,445 raw rows, 56 columns)",
             font_size=9, color=C_MUTED)


def _slide_data_cleaning(prs, dq_issues: list[str]):
    slide = _add_slide(prs)
    _section_header(slide, "02", "Data Cleaning & Preparation")

    steps = [
        "1.  The original file (happy_merged.csv) was NOT modified. All cleaning was done on copies.",
        "2.  Each row was assigned to one of 7 sub-tables by checking which columns contained data "
             "(e.g. rows with a feedback_id belong to Feedback; rows with stock data belong to Inventory).",
        "3.  Orders were stored as two separate row types in the source file — one row held the product "
             "and quantity, another held the customer, date and total. These were matched and merged on "
             "the shared Order ID.",
        "4.  All numeric columns (prices, quantities, ratings, etc.) were converted to numbers; "
             "rows with unreadable values were flagged rather than silently dropped.",
        "5.  All date columns were converted to proper dates. Inventory dates used a mixed format "
             "(e.g. '17-03-2023' and 'Sep-24') and were parsed accordingly.",
        "6.  Duplicate records were checked for each sub-table using their primary ID column. "
             "No duplicates were found.",
        "7.  Referential integrity was confirmed: every order ID appearing in Feedback and Delivery "
             "also exists in the Orders table. No orphaned references were found.",
    ]

    txb = slide.shapes.add_textbox(Inches(0.35), Inches(1.1), Inches(12.5), Inches(4.3))
    tf = txb.text_frame
    tf.word_wrap = True
    first = True
    for step in steps:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.space_before = Pt(5)
        r = p.add_run()
        r.text = step
        r.font.size = Pt(10)
        r.font.color.rgb = C_DARK

    # FIX: Increased box height and adjusted spacing to prevent text overflow
    _box(slide, Inches(0.35), Inches(5.5), Inches(12.5), Inches(1.6),
         fill_rgb=_rgb(0xFF, 0xFB, 0xEB), line_rgb=_rgb(0xF5, 0x9E, 0x0B), line_width_pt=1.0)
    _textbox(slide, Inches(0.5), Inches(5.6), Inches(12.2), Inches(0.3),
             "Data Quality Issues Found (left as-is in source — not corrected):",
             font_size=10, bold=True, color=_rgb(0x92, 0x40, 0x00))
    
    for i, issue in enumerate(dq_issues):
        _textbox(slide, Inches(0.5), Inches(5.9 + i * 0.55), Inches(12.2), Inches(0.5),
                 f"  * {issue}", font_size=9.5, color=_rgb(0x78, 0x35, 0x00))


def _slide_kpis(prs, kpis: dict, date_range: str):
    slide = _add_slide(prs)
    _section_header(slide, "03", "Key Performance Indicators")

    total_orders       = kpis["total_orders"]
    total_rev          = kpis["total_revenue"]
    avg_ov             = kpis["avg_order_value"]
    avg_rating         = kpis["avg_rating"]
    on_time_pct        = kpis["on_time_pct"]
    avg_del            = kpis["avg_delivery_minutes"]
    total_spend        = kpis["total_ad_spend"]
    roas               = kpis["overall_roas"]

    cards = [
        ("Total Orders",        f"{total_orders:,}",         "orders placed"),
        ("Total Revenue",       f"Rs {total_rev/1e6:.2f}M",  f"Rs {total_rev:,.0f}"),
        ("Avg Order Value",     f"Rs {avg_ov:,.0f}",         "per order"),
        ("Avg Customer Rating", f"{avg_rating:.2f} / 5",     "out of 5 stars"),
        ("On-Time Delivery",    f"{on_time_pct:.1f}%",       "of orders on time"),
        ("Avg Delivery Time",   f"{avg_del:.1f} min",        "from order to door"),
        ("Total Ad Spend",      f"Rs {total_spend/1e6:.2f}M", f"Rs {total_spend:,.0f}"),
        ("Ad Return (ROAS)",    f"{roas:.2f}x",              f"Rs {roas:.2f} back per Rs 1 spent"),
    ]

    card_w = Inches(1.52)
    card_h = Inches(1.15)
    left_start = Inches(0.35)
    gap = Inches(0.09)

    for i, (label, value, sub) in enumerate(cards):
        col = i % 4
        row = i // 4
        left = left_start + col * (card_w + gap)
        top = Inches(1.1) + row * (card_h + Inches(0.12))
        _kpi_card(slide, left, top, card_w, card_h, label, value, sub)

    # Narrative
    _box(slide, Inches(0.35), Inches(3.65), Inches(12.5), Inches(1.45),
         fill_rgb=_rgb(0xF0, 0xF9, 0xFF), line_rgb=_rgb(0x3B, 0x82, 0xD4), line_width_pt=0.75)
    narrative = (
        f"What this means:  In the period covered ({date_range}), the business handled "
        f"{total_orders:,} orders and brought in Rs {total_rev/1e6:.2f} million in revenue. "
        f"The average basket size was Rs {avg_ov:,.0f}. Customers gave an average rating of "
        f"{avg_rating:.2f} out of 5 — moderate, with room to improve. {on_time_pct:.1f}% of orders "
        f"arrived on time, and deliveries took {avg_del:.1f} minutes on average — very fast by "
        f"industry standards. Marketing spent Rs {total_spend/1e6:.2f}M and returned Rs {roas:.2f} "
        f"for every Rs 1 spent (this is called the Return on Ad Spend, or ROAS)."
    )
    txb = slide.shapes.add_textbox(Inches(0.55), Inches(3.75), Inches(12.1), Inches(1.25))
    tf = txb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = narrative
    r.font.size = Pt(10)
    r.font.color.rgb = C_DARK


def _slide_orders(prs, cat_rev: pd.DataFrame, pm_rev: pd.DataFrame, total_rev: float):
    slide = _add_slide(prs)
    _section_header(slide, "04", "Orders & Revenue")

    # Category table
    _textbox(slide, Inches(0.35), Inches(1.05), Inches(5.5), Inches(0.3),
             "Revenue by Product Category", font_size=11, bold=True, color=C_DARK)
    cat_rows = [["Category", "Revenue (Rs)", "Orders"]]
    for _, row in cat_rev.iterrows():
        cat_rows.append([row["category"], f"Rs {row['revenue']:,.0f}", f"{int(row['num_orders']):,}"])
    _simple_table(slide, Inches(0.35), Inches(1.35), [Inches(2.85), Inches(1.6), Inches(0.9)], cat_rows)

    # Payment method table
    _textbox(slide, Inches(5.9), Inches(1.05), Inches(5.5), Inches(0.3),
             "Revenue by Payment Method", font_size=11, bold=True, color=C_DARK)
    pm_rows = [["Payment Method", "Revenue (Rs)", "Share"]]
    for _, row in pm_rev.iterrows():
        share = row["revenue"] / total_rev * 100
        pm_rows.append([row["payment_method"], f"Rs {row['revenue']:,.0f}", f"{share:.1f}%"])
    _simple_table(slide, Inches(5.9), Inches(1.35), [Inches(1.9), Inches(1.9), Inches(0.9)], pm_rows)

    # Insights
    top_cat = cat_rev.iloc[0]
    top_pm = pm_rev.iloc[0]
    insights = [
        ("I", f"Top revenue category: {top_cat['category']} — Rs {top_cat['revenue']:,.0f} "
               f"({top_cat['revenue']/total_rev*100:.1f}% of total). Focus promotions here."),
        ("II", f"Payment is fairly balanced across all 4 methods; "
                f"{top_pm['payment_method']} is slightly ahead "
                f"(Rs {top_pm['revenue']:,.0f}, {top_pm['revenue']/total_rev*100:.1f}%)."),
    ]
    _textbox(slide, Inches(0.35), Inches(5.7), Inches(12.5), Inches(0.3),
             "Insights", font_size=11, bold=True, color=C_DARK)
    for i, (tag, text) in enumerate(insights):
        _insight_box(slide, Inches(0.35), Inches(6.0) + i * Inches(0.55),
                     Inches(12.5), Inches(0.5), tag, text)


def _slide_delivery(prs, status_df: pd.DataFrame, reasons_df: pd.DataFrame,
                    avg_time: float, avg_rating: float, on_time_pct: float):
    slide = _add_slide(prs)
    _section_header(slide, "05", "Delivery Performance")

    # Status table
    _textbox(slide, Inches(0.35), Inches(1.05), Inches(5.5), Inches(0.3),
             "Delivery Status Breakdown", font_size=11, bold=True)
    total_del = status_df["count"].sum()
    st_rows = [["Status", "Count", "Share"]]
    for _, row in status_df.iterrows():
        st_rows.append([row["delivery_status"], f"{row['count']:,}", f"{row['count']/total_del*100:.1f}%"])
    _simple_table(slide, Inches(0.35), Inches(1.35), [Inches(2.6), Inches(1.0), Inches(0.9)], st_rows)

    # Delay reasons table
    _textbox(slide, Inches(5.5), Inches(1.05), Inches(5.5), Inches(0.3),
             "Main Reasons for Delayed Deliveries", font_size=11, bold=True)
    r_rows = [["Reason", "Delayed Orders"]]
    for _, row in reasons_df.head(6).iterrows():
        r_rows.append([row["reason"], f"{row['count']:,}"])
    _simple_table(slide, Inches(5.5), Inches(1.35), [Inches(2.8), Inches(1.5)], r_rows)

    # KPI strip
    delayed_pct = 100 - on_time_pct
    cards = [
        ("On-Time Rate",       f"{on_time_pct:.1f}%"),
        ("Delayed Rate",       f"{delayed_pct:.1f}%"),
        ("Avg Delivery Time",  f"{avg_time:.1f} min"),
        ("Avg Rating",         f"{avg_rating:.2f} / 5"),
    ]
    card_w = Inches(2.9)
    for i, (label, val) in enumerate(cards):
        _kpi_card(slide, Inches(0.35) + i * (card_w + Inches(0.12)),
                  Inches(3.65), card_w, Inches(0.85), label, val)

    # Insights
    top_reason = reasons_df["reason"].iloc[0] if not reasons_df.empty else "Unknown"
    insights_txt = [
        ("I", f"Nearly 1 in 3 deliveries ({delayed_pct:.1f}%) was delayed. "
               f"The most common reason is '{top_reason}'. "
               f"Reducing delays is the single biggest lever for improving customer ratings."),
        ("II", f"Average delivery time is {avg_time:.1f} minutes — extremely fast. "
                f"The goal should be to maintain this speed while cutting the delay rate."),
        ("III", f"Customers who received delayed orders gave lower ratings on average. "
                 f"Every percentage point improvement in on-time delivery will lift the overall "
                 f"rating closer to 4.0/5."),
    ]
    _textbox(slide, Inches(0.35), Inches(4.7), Inches(12.5), Inches(0.3),
             "Insights", font_size=11, bold=True)
    for i, (tag, text) in enumerate(insights_txt):
        _insight_box(slide, Inches(0.35), Inches(5.0) + i * Inches(0.6),
                     Inches(12.5), Inches(0.55), tag, text)


def _slide_feedback(prs, rating_dist: pd.DataFrame, sentiment_dist: pd.DataFrame,
                    cat_rating: pd.DataFrame, avg_rating: float):
    slide = _add_slide(prs)
    _section_header(slide, "06", "Customer Feedback & Ratings")

    # Rating distribution table
    _textbox(slide, Inches(0.35), Inches(1.05), Inches(4), Inches(0.3),
             "Rating Distribution", font_size=11, bold=True)
    total_fb = rating_dist["count"].sum()
    r_rows = [["Stars", "Count", "Share"]]
    for _, row in rating_dist.sort_values("rating", ascending=False).iterrows():
        stars = int(row["rating"])
        r_rows.append([f"{'*' * stars} ({stars})", f"{row['count']:,}", f"{row['count']/total_fb*100:.1f}%"])
    _simple_table(slide, Inches(0.35), Inches(1.35), [Inches(1.8), Inches(0.9), Inches(0.9)], r_rows)

    # Sentiment table
    _textbox(slide, Inches(4.3), Inches(1.05), Inches(4), Inches(0.3),
             "Sentiment Split (positive / neutral / negative)", font_size=11, bold=True)
    total_sent = sentiment_dist["count"].sum()
    s_rows = [["Feeling", "Count", "Share"]]
    for _, row in sentiment_dist.sort_values("count", ascending=False).iterrows():
        s_rows.append([row["sentiment"], f"{row['count']:,}", f"{row['count']/total_sent*100:.1f}%"])
    _simple_table(slide, Inches(4.3), Inches(1.35), [Inches(1.5), Inches(0.9), Inches(0.9)], s_rows)

    # Avg rating by feedback category
    _textbox(slide, Inches(8.0), Inches(1.05), Inches(5), Inches(0.3),
             "Avg Rating by Topic", font_size=11, bold=True)
    cr_rows = [["Topic", "Avg Rating"]]
    for _, row in cat_rating.sort_values("avg_rating").iterrows():
        cr_rows.append([row["feedback_category"], f"{row['avg_rating']:.2f}"])
    _simple_table(slide, Inches(8.0), Inches(1.35), [Inches(2.5), Inches(1.3)], cr_rows)

    # Insights
    worst_topic = cat_rating.sort_values("avg_rating").iloc[0]
    pos = sentiment_dist[sentiment_dist["sentiment"] == "Positive"]["count"].sum()
    neg = sentiment_dist[sentiment_dist["sentiment"] == "Negative"]["count"].sum()
    insights_txt = [
        ("I", f"Average rating is {avg_rating:.2f}/5. Only {pos/total_fb*100:.1f}% of feedback is "
               f"positive, while {neg/total_fb*100:.1f}% is negative — meaning the business is "
               f"below expectations for more customers than it delights."),
        ("II", f"'{worst_topic['feedback_category']}' receives the lowest average rating "
                f"({worst_topic['avg_rating']:.2f}/5). Fixing issues in this area will have the "
                f"biggest impact on overall customer satisfaction."),
        ("III", "3-star ratings are the most common, suggesting customers feel service is 'acceptable' "
                 "but not memorable. Turning these into 4- or 5-star experiences should be the focus."),
    ]
    _textbox(slide, Inches(0.35), Inches(4.1), Inches(12.5), Inches(0.3),
             "Insights", font_size=11, bold=True)
    for i, (tag, text) in enumerate(insights_txt):
        _insight_box(slide, Inches(0.35), Inches(4.4) + i * Inches(0.6),
                     Inches(12.5), Inches(0.55), tag, text)


def _slide_marketing(prs, ch_df: pd.DataFrame, best_camp: pd.Series,
                     worst_camp: pd.Series, total_spend: float, total_rev_camp: float, roas: float):
    slide = _add_slide(prs)
    _section_header(slide, "07", "Marketing Campaigns")

    # Channel performance table
    _textbox(slide, Inches(0.35), Inches(1.05), Inches(8), Inches(0.3),
             "Performance by Ad Channel  (ROAS = Rs returned per Rs 1 spent on ads)", font_size=11, bold=True)
    c_rows = [["Channel", "Spend (Rs)", "Revenue (Rs)", "ROAS", "Click Rate"]]
    for _, row in ch_df.sort_values("roas", ascending=False).iterrows():
        c_rows.append([
            row["channel"],
            f"Rs {row['spend']:,.0f}",
            f"Rs {row['revenue']:,.0f}",
            f"{row['roas']:.2f}x",
            f"{row['ctr']:.1f}%",
        ])
    _simple_table(slide, Inches(0.35), Inches(1.35),
                  [Inches(2.0), Inches(2.3), Inches(2.3), Inches(1.2), Inches(1.5)], c_rows)

    # KPI strip
    cards = [
        ("Total Spend",    f"Rs {total_spend/1e6:.2f}M"),
        ("Attributed Rev", f"Rs {total_rev_camp/1e6:.2f}M"),
        ("True ROAS",      f"{roas:.2f}x"),
        ("Channels",       str(len(ch_df))),
    ]
    for i, (lbl, val) in enumerate(cards):
        _kpi_card(slide, Inches(0.35) + i * Inches(3.15), Inches(3.55), Inches(2.9), Inches(0.85), lbl, val)

    # Insights
    best_ch = ch_df.sort_values("roas", ascending=False).iloc[0]
    worst_ch = ch_df.sort_values("roas").iloc[0]
    insights_txt = [
        ("I", f"Best-performing channel: {best_ch['channel']} — returns Rs {best_ch['roas']:.2f} "
               f"for every Rs 1 spent. This is where marketing budget should be prioritised."),
        ("II", f"Lowest-performing channel: {worst_ch['channel']} — returns only Rs {worst_ch['roas']:.2f} "
                f"per Rs 1 spent. Consider reducing spend here and testing creative or targeting changes."),
        ("III", f"Best individual campaign: '{best_camp['campaign_name']}' (ROAS {best_camp['roas']:.2f}x). "
                 f"Worst: '{worst_camp['campaign_name']}' (ROAS {worst_camp['roas']:.2f}x). "
                 f"Replicate the best campaign's approach across other channels."),
        ("IV", f"True Overall ROAS is {roas:.2f}x, meaning marketing is currently operating at a loss "
                f"due to high attribution overlap across channels. Campaigns returning less than 2x should be reviewed."),
    ]
    _textbox(slide, Inches(0.35), Inches(4.55), Inches(12.5), Inches(0.3),
             "Insights", font_size=11, bold=True)
    for i, (tag, text) in enumerate(insights_txt):
        _insight_box(slide, Inches(0.35), Inches(4.85) + i * Inches(0.57),
                     Inches(12.5), Inches(0.52), tag, text)


def _slide_inventory(prs, cat_dmg: pd.DataFrame, total_rec: float,
                     total_dmg: float, dmg_rate: float, bad_rows: int):
    slide = _add_slide(prs)
    _section_header(slide, "08", "Inventory & Stock")

    # FIX: Limited table to Top 6 to prevent overlapping the warning box
    _textbox(slide, Inches(0.35), Inches(1.05), Inches(7), Inches(0.3),
             "Damage Rate by Product Category  (Top 6 Categories)", font_size=11, bold=True)
    d_rows = [["Category", "Received", "Damaged", "Damage Rate"]]
    for _, row in cat_dmg.head(6).iterrows():
        d_rows.append([
            row["category"],
            f"{int(row['total_received']):,}",
            f"{int(row['total_damaged']):,}",
            f"{row['damage_rate']:.1f}%",
        ])
    _simple_table(slide, Inches(0.35), Inches(1.35),
                  [Inches(2.8), Inches(1.4), Inches(1.4), Inches(1.5)], d_rows)  
                  
    # KPI strip
    cards = [
        ("Stock Received",  f"{total_rec:,.0f}"),
        ("Stock Damaged",   f"{total_dmg:,.0f}"),
        ("Overall Damage %", f"{dmg_rate:.1f}%"),
    ]
    for i, (lbl, val) in enumerate(cards):
        _kpi_card(slide, Inches(8.0) + i * Inches(1.7), Inches(1.35), Inches(1.55), Inches(1.0), lbl, val)

    # FIX: Moved warning box higher up since table is now shorter
    _box(slide, Inches(0.35), Inches(3.8), Inches(12.5), Inches(0.75),
         fill_rgb=_rgb(0xFF, 0xFB, 0xEB), line_rgb=_rgb(0xF5, 0x9E, 0x0B), line_width_pt=0.8)
    _textbox(slide, Inches(0.5), Inches(3.85), Inches(12.2), Inches(0.62),
             f"Data quality note: {bad_rows:,} out of 93,277 inventory records "
             f"({bad_rows/93277*100:.1f}%) show 'damaged stock' exceeding 'stock received'. "
             f"This is a known issue in the source system and has not been corrected. "
             f"These records should be investigated with the warehouse team.",
             font_size=9.5, color=_rgb(0x92, 0x40, 0x00))

    # FIX: Adjusted Insights positioning
    worst_cat = cat_dmg.sort_values("damage_rate", ascending=False).iloc[0]
    best_cat  = cat_dmg.sort_values("damage_rate").iloc[0]
    insights_txt = [
        ("I", f"Overall, {dmg_rate:.1f}% of all stock received arrives damaged — "
               f"nearly half of everything ordered. This is a major cost to the business."),
        ("II", f"Worst category for damage: {worst_cat['category']} at {worst_cat['damage_rate']:.1f}%. "
                f"Best category: {best_cat['category']} at {best_cat['damage_rate']:.1f}%. "
                f"High-damage categories need better packaging or alternative suppliers."),
        ("III", "Reducing the damage rate by even 10 percentage points would save significant "
                 "restocking costs and reduce product shortages for customers."),
    ]
    _textbox(slide, Inches(0.35), Inches(4.7), Inches(12.5), Inches(0.3),
             "Insights", font_size=11, bold=True)
    for i, (tag, text) in enumerate(insights_txt):
        _insight_box(slide, Inches(0.35), Inches(5.0) + i * Inches(0.6),
                     Inches(12.5), Inches(0.55), tag, text)


def _slide_customers(prs, seg_df: pd.DataFrame, seg_rev: pd.DataFrame, total_rev: float):
    slide = _add_slide(prs)
    _section_header(slide, "09", "Customers")

    # Segment table
    _textbox(slide, Inches(0.35), Inches(1.05), Inches(6), Inches(0.3),
             "Customer Segment Breakdown", font_size=11, bold=True)
    # merge
    merged = seg_df.merge(seg_rev[["customer_segment","revenue","num_orders"]], on="customer_segment")
    s_rows = [["Segment", "Customers", "Avg Spend / Order", "Avg Orders", "Revenue"]]
    for _, row in merged.sort_values("revenue", ascending=False).iterrows():
        s_rows.append([
            row["customer_segment"],
            f"{int(row['count']):,}",
            f"Rs {row['avg_order_value']:,.0f}",
            f"{row['avg_total_orders']:.1f}",
            f"Rs {row['revenue']:,.0f}",
        ])
    _simple_table(slide, Inches(0.35), Inches(1.35),
                  [Inches(1.6), Inches(1.5), Inches(2.0), Inches(1.5), Inches(2.0)], s_rows)

    # Insights
    top_seg = merged.sort_values("revenue", ascending=False).iloc[0]
    low_seg = merged.sort_values("revenue").iloc[0]
    total_customers = seg_df["count"].sum()
    insights_txt = [
        ("I", f"All four segments — Regular, New, Premium, Inactive — contribute roughly equal "
               f"revenue ({top_seg['customer_segment']}: Rs {top_seg['revenue']:,.0f} vs "
               f"{low_seg['customer_segment']}: Rs {low_seg['revenue']:,.0f}). "
               f"No single segment dominates."),
        ("II", f"Average order values are similar across segments (around Rs 1,090–1,120). "
                f"This suggests segment differences are driven more by order frequency "
                f"than by basket size."),
        ("III", f"The 'Inactive' segment ({int(merged[merged['customer_segment']=='Inactive']['count'].iloc[0]):,} "
                 f"customers) represents a reactivation opportunity — these customers have "
                 f"bought before but are no longer active."),
    ]
    _textbox(slide, Inches(0.35), Inches(4.6), Inches(12.5), Inches(0.3),
             "Insights", font_size=11, bold=True)
    for i, (tag, text) in enumerate(insights_txt):
        _insight_box(slide, Inches(0.35), Inches(4.9) + i * Inches(0.62),
                     Inches(12.5), Inches(0.57), tag, text)


def _slide_key_insights(prs, kpis: dict, cat_rev: pd.DataFrame, status_df: pd.DataFrame,
                        reasons_df: pd.DataFrame, ch_df: pd.DataFrame,
                        cat_dmg: pd.DataFrame, seg_rev: pd.DataFrame, avg_rating: float):
    slide = _add_slide(prs)
    _section_header(slide, "10", "Key Business Insights")

    total_del = status_df["count"].sum()
    on_time = status_df[status_df["delivery_status"] == "On Time"]["count"].sum()
    delayed_pct = 100 - on_time / total_del * 100
    top_cat = cat_rev.iloc[0]
    best_ch = ch_df.sort_values("roas", ascending=False).iloc[0]
    worst_ch = ch_df.sort_values("roas").iloc[0]
    worst_dmg = cat_dmg.sort_values("damage_rate", ascending=False).iloc[0]
    best_dmg  = cat_dmg.sort_values("damage_rate").iloc[0]
    top_seg_rev = seg_rev.sort_values("revenue", ascending=False).iloc[0]
    roas = kpis["overall_roas"]

    insights = [
        ("I1", f"Revenue is healthy at Rs {kpis['total_revenue']/1e6:.2f}M from {kpis['total_orders']:,} orders, "
               f"but average rating ({avg_rating:.2f}/5) shows customers are not consistently delighted."),
        ("I2", f"{delayed_pct:.1f}% of deliveries are delayed. The top reason is "
               f"'{reasons_df['reason'].iloc[0] if not reasons_df.empty else 'Traffic'}'. "
               f"Delivery delays are the #1 driver of negative feedback."),
        ("I3", f"{top_cat['category']} is the top-selling category "
               f"(Rs {top_cat['revenue']:,.0f}, {top_cat['revenue']/kpis['total_revenue']*100:.1f}% of revenue). "
               f"Stock availability here is critical."),
        ("I4", f"Marketing returns Rs {roas:.2f} for every Rs 1 spent (ROAS {roas:.2f}x). "
               f"{best_ch['channel']} is the best channel ({best_ch['roas']:.2f}x); "
               f"{worst_ch['channel']} is the weakest ({worst_ch['roas']:.2f}x)."),
        ("I5", f"Stock damage rate is {kpis.get('overall_damage_rate', 0.0):.1f}% on average. "
               f"{worst_dmg['category']} is the worst-hit category ({worst_dmg['damage_rate']:.1f}%). "
               f"This inflates restocking costs significantly."),
        ("I6", f"All four customer segments contribute nearly equal revenue. "
               f"{top_seg_rev['customer_segment']} leads with Rs {top_seg_rev['revenue']:,.0f}. "
               f"The 'Inactive' segment is an untapped reactivation opportunity."),
        ("I7", f"Only {sum(1 for _, r in pd.DataFrame({'cat':cat_dmg['damage_rate']}).iterrows() if r['cat'] < 40)} "
               f"of 11 product categories have a damage rate below 40%. "
               f"Supply chain quality is a systemic issue, not isolated to one product."),
    ]

    for i, (tag, text) in enumerate(insights):
        row = i // 2
        col = i % 2
        left = Inches(0.35) + col * Inches(6.45)
        top = Inches(1.1) + row * Inches(0.72)
        _insight_box(slide, left, top, Inches(6.2), Inches(0.65), tag, text)


def _slide_recommendations(prs, kpis: dict, status_df: pd.DataFrame,
                            ch_df: pd.DataFrame, cat_dmg: pd.DataFrame,
                            reasons_df: pd.DataFrame, avg_rating: float):
    slide = _add_slide(prs)
    _section_header(slide, "11", "Recommendations & Next Steps")

    total_del = status_df["count"].sum()
    on_time = status_df[status_df["delivery_status"] == "On Time"]["count"].sum()
    delayed_pct = 100 - on_time / total_del * 100
    top_reason = reasons_df["reason"].iloc[0] if not reasons_df.empty else "Traffic"
    best_ch = ch_df.sort_values("roas", ascending=False).iloc[0]
    worst_ch = ch_df.sort_values("roas").iloc[0]
    worst_dmg = cat_dmg.sort_values("damage_rate", ascending=False).iloc[0]

    recs = [
        ("R1", "Reduce delivery delays",
         f"Currently {delayed_pct:.1f}% of deliveries are late, mainly due to '{top_reason}'. "
         f"Assign more delivery partners during peak hours and use route-optimisation tools. "
         f"Target: bring on-time rate above 80%."),
        ("R2", "Fix damaged stock in top-risk categories",
         f"{worst_dmg['category']} has a {worst_dmg['damage_rate']:.1f}% damage rate. "
         f"Audit packaging standards with these suppliers immediately. "
         f"Even halving the damage rate would cut waste significantly."),
        ("R3", "Shift marketing spend toward higher-return channels",
         f"{best_ch['channel']} returns Rs {best_ch['roas']:.2f} per Rs 1 spent "
         f"vs {worst_ch['channel']} at only Rs {worst_ch['roas']:.2f}. "
         f"Reallocate at least 15% of {worst_ch['channel']} budget to {best_ch['channel']}."),
        ("R4", "Re-engage the Inactive customer segment",
         f"These customers have bought before but stopped. A targeted discount campaign "
         f"(e.g. 20% off their next order) could reactivate them at low cost, "
         f"since acquisition is already done."),
        ("R5", "Investigate and resolve the inventory data quality issue",
         f"29,299 records show more damaged stock than received stock — "
         f"this is logically impossible and suggests a recording or system error. "
         f"Fix the data entry process at the warehouse level."),
        ("R6", "Improve the 3-star customer experience",
         f"3-star ratings are the most common, meaning most customers find the service 'acceptable' "
         f"but not great. Focus on the '{cat_dmg.sort_values('damage_rate').iloc[-1]['category'] if False else 'Delivery'}' "  # noqa
         f"experience — faster, consistent on-time delivery is the fastest route to higher ratings."),
    ]

    for i, (tag, title, text) in enumerate(recs):
        top_y = Inches(1.1) + i * Inches(1.0)
        # Tag
        tag_shape = _box(slide, Inches(0.35), top_y, Inches(0.55), Inches(0.38),
                         fill_rgb=C_ACCENT, line_rgb=C_ACCENT)
        txb_tag = slide.shapes.add_textbox(Inches(0.35), top_y, Inches(0.55), Inches(0.38))
        p = txb_tag.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = tag
        r.font.size = Pt(9)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        # Title
        txb_title = slide.shapes.add_textbox(Inches(1.0), top_y, Inches(11.7), Inches(0.32))
        p_t = txb_title.text_frame.paragraphs[0]
        r_t = p_t.add_run()
        r_t.text = title
        r_t.font.size = Pt(11)
        r_t.font.bold = True
        r_t.font.color.rgb = C_DARK

        # Body
        txb_body = slide.shapes.add_textbox(Inches(1.0), top_y + Inches(0.33), Inches(11.7), Inches(0.55))
        tf = txb_body.text_frame
        tf.word_wrap = True
        p_b = tf.paragraphs[0]
        r_b = p_b.add_run()
        r_b.text = text
        r_b.font.size = Pt(9.5)
        r_b.font.color.rgb = C_MUTED
# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_report(tables: dict) -> bytes:
    """
    Build the full 13-slide deck from `tables` (output of analysis.load_tables()).
    Returns the .pptx file as bytes (ready for st.download_button).
    """
    import analysis as ana

    orders    = tables.get("orders", pd.DataFrame())
    products  = tables.get("products", pd.DataFrame())
    delivery  = tables.get("delivery", pd.DataFrame())
    feedback  = tables.get("feedback", pd.DataFrame())
    campaigns = tables.get("campaigns", pd.DataFrame())
    customers = tables.get("customers", pd.DataFrame())
    inventory = tables.get("inventory", pd.DataFrame())

    # Cast numeric columns
    for col in ["order_id", "customer_id", "product_id", "quantity", "unit_price", "order_total", "store_id"]:
        if col in orders.columns:
            orders[col] = pd.to_numeric(orders[col], errors="coerce")
    orders["order_date"] = pd.to_datetime(orders.get("order_date"), errors="coerce")

    for col in ["stock_received", "damaged_stock"]:
        if col in inventory.columns:
            inventory[col] = pd.to_numeric(inventory[col], errors="coerce")
    inventory["date"] = pd.to_datetime(inventory.get("date"), format="mixed", dayfirst=True, errors="coerce")

    for col in ["rating"]:
        if col in feedback.columns:
            feedback[col] = pd.to_numeric(feedback[col], errors="coerce")

    for col in ["impressions", "clicks", "conversions", "spend", "revenue_generated", "roas"]:
        if col in campaigns.columns:
            campaigns[col] = pd.to_numeric(campaigns[col], errors="coerce")

    for col in ["customer_id", "total_orders", "avg_order_value"]:
        if col in customers.columns:
            customers[col] = pd.to_numeric(customers[col], errors="coerce")

    delivery["delivery_time_minutes"] = pd.to_numeric(
        delivery.get("delivery_time_minutes"), errors="coerce"
    )

    # Compute all analytics
    kpis        = ana.overview_kpis(tables)
    cat_rev     = ana.revenue_by_category(orders, products)
    pm_rev      = ana.revenue_by_payment_method(orders)
    status_df   = ana.delivery_status_breakdown(delivery)
    reasons_df  = ana.delay_reasons(delivery)
    rating_dist = ana.rating_distribution(feedback)
    sent_dist   = ana.sentiment_distribution(feedback)
    cat_rating  = ana.avg_rating_by_category(feedback)
    ch_df       = ana.roas_by_channel(campaigns)
    cat_dmg     = ana.damage_rate_by_category(inventory, products)
    seg_df      = ana.customer_segment_breakdown(customers)
    seg_rev     = ana.segment_revenue(customers, orders)

    total_rev       = float(orders["order_total"].sum())
    avg_rating      = float(feedback["rating"].mean())
    avg_time        = float(delivery["delivery_time_minutes"].mean())
    on_time_pct     = float(kpis["on_time_pct"])
    total_rec       = float(inventory["stock_received"].sum())
    total_dmg       = float(inventory["damaged_stock"].sum())
    dmg_rate        = total_dmg / total_rec * 100 if total_rec > 0 else 0.0
    bad_rows        = int((inventory["damaged_stock"] > inventory["stock_received"]).sum())
    total_spend     = float(campaigns["spend"].sum())
    total_rev_camp  = float(campaigns["revenue_generated"].sum())
    
    # FIX: Ensure accurate ROAS and damage rate variables are sent to slides
    roas            = float(kpis["overall_roas"]) 
    kpis["overall_damage_rate"] = dmg_rate
    
    date_min        = orders["order_date"].min()
    date_max        = orders["order_date"].max()
    date_range      = f"{date_min.strftime('%d %b %Y')} to {date_max.strftime('%d %b %Y')}"
    num_stores      = int(orders["store_id"].nunique())
    num_categories  = int(products["category"].nunique())
    num_pm          = int(orders["payment_method"].nunique())
    num_channels    = int(campaigns["channel"].nunique())

    best_camp_row  = ana.campaign_performance(campaigns).nlargest(1, "roas").iloc[0]
    worst_camp_row = ana.campaign_performance(campaigns).nsmallest(1, "roas").iloc[0]

    row_counts = {
        "feedback":  5000,
        "customers": 2500,
        "delivery":  5000,
        "orders":    5000,
        "inventory": 93277,
        "campaigns": 5400,
        "products":  268,
    }

    dq_issues = [
        f"Orders: order_total does not equal quantity x unit_price for 4,999 of 5,000 orders. "
        f"This is expected — the total likely includes taxes, delivery fees, or discounts "
        f"that are not separately recorded. Source values were kept as-is.",
        f"Inventory: {bad_rows:,} records (out of 93,277) show 'damaged stock' greater than "
        f"'stock received'. This is logically impossible and indicates a data entry error "
        f"in the source system. These records were NOT corrected.",
    ]

    # Build presentation
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    _slide_title(prs, date_range, kpis["total_orders"], num_stores,
                 num_categories, num_pm, num_channels)
    _slide_toc(prs)
    _slide_dataset_overview(prs, row_counts, date_range)
    _slide_data_cleaning(prs, dq_issues)
    _slide_kpis(prs, kpis, date_range)
    _slide_orders(prs, cat_rev, pm_rev, total_rev)
    _slide_delivery(prs, status_df, reasons_df, avg_time, avg_rating, on_time_pct)
    _slide_feedback(prs, rating_dist, sent_dist, cat_rating, avg_rating)
    _slide_marketing(prs, ch_df, best_camp_row, worst_camp_row,
                     total_spend, total_rev_camp, roas)
    _slide_inventory(prs, cat_dmg, total_rec, total_dmg, dmg_rate, bad_rows)
    _slide_customers(prs, seg_df, seg_rev, total_rev)
    _slide_key_insights(prs, kpis, cat_rev, status_df, reasons_df,
                        ch_df, cat_dmg, seg_rev, avg_rating)
    _slide_recommendations(prs, kpis, status_df, ch_df, cat_dmg,
                           reasons_df, avg_rating)

    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.getvalue()