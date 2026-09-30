# Blinkit Operations Analytics Dashboard

## Project Overview

An end-to-end data analytics project for a quick-commerce (rapid-delivery grocery/retail) business. The project ingests a single merged CSV export (`happy_merged.csv`), splits it into seven normalized sub-tables, cleans and validates each, computes cross-table business analytics, and presents the findings in an interactive Streamlit dashboard with Plotly visualizations.

**Stack:** Python · Pandas · Streamlit · Plotly · openpyxl

---

## Objective

Transform raw operational data into actionable business insights across Orders & Revenue, Delivery Performance, Customer Feedback & Ratings, Marketing Campaigns, Inventory & Stock, and Customer Analytics.

---

## Dataset Description

### Primary Source
`data/raw/happy_merged.csv` — 121,445 rows × 56 columns.

This file is **not** a single flat table. It is a **vertically stacked / merged export** of seven independent business tables. Each row belongs to exactly one logical table, identified by which columns are populated and which are blank.

### Hidden Sub-Tables (Un-Merged Structure)

| Sub-table | Key Identifier | Rows | Cols |
|-----------|---------------|------|------|
| feedback | `feedback_id` non-null | 5,000 | 8 |
| customers | `customer_name` non-null | 2,500 | 11 |
| delivery | `promised_time` non-null | 5,000 | 8 |
| orders | joined from two row types (see below) | 5,000 | 11 |
| inventory | `stock_received` non-null | 93,277 | 4 |
| campaigns | `campaign_id` non-null | 5,400 | 10 |
| products | `product_name` non-null | 268 | 10 |

**Row count verification:** 5,000 + 2,500 + 5,000 + (5,000×2 for orders' two row types) + 93,277 + 5,400 + 268 = **121,445** ✓ — matches perfectly.

### Optional Icon Files
- `data/raw/Category_Icons.xlsx` — maps 11 product categories to image URLs (columns: `category`, `Img`)
- `data/raw/Rating_Icon.xlsx` — maps ratings 1–5 to emoji URLs and star strings (columns: `Rating`, `Emoji`, `Star`)

Both files are present and are used in the dashboard to enhance the Feedback & Ratings tab.

---

## Data Splitting Methodology

**File:** `src/data_splitting.py`

The splitting logic was determined by programmatic analysis of non-null column co-occurrence patterns in the merged CSV (not assumed in advance):

1. **Feedback rows** — extracted where `feedback_id` is non-null. Contains: `feedback_id, order_id, customer_id, rating, feedback_text, feedback_category, sentiment, feedback_date`.

2. **Customer rows** — extracted where `customer_name` is non-null. Contains: `customer_id, customer_name, email, phone, address, area, pincode, registration_date, customer_segment, total_orders, avg_order_value`.

3. **Delivery rows** — extracted where `promised_time` is non-null (Type A). Contains: `order_id, delivery_partner_id, promised_time, actual_time, delivery_time_minutes, distance_km, delivery_status, reasons_if_delayed`.

4. **Orders** — **Important discovery**: each order is stored as TWO separate row types in the merged file:
   - **Type B (order headers):** rows where `delivery_partner_id` is non-null AND `promised_time` is null → contains `order_id, customer_id, delivery_status, order_date, order_total, payment_method, store_id`
   - **Order item rows:** rows where `quantity` is non-null → contains `order_id, product_id, quantity, unit_price`
   
   These are joined on `order_id` (inner join, all 5,000 match perfectly) to produce the unified `orders` sub-table.

5. **Inventory rows** — extracted where `stock_received` is non-null. Contains: `product_id, date, stock_received, damaged_stock`.

6. **Campaign rows** — extracted where `campaign_id` is non-null. Contains: `campaign_id, campaign_name, target_audience, channel, impressions, clicks, conversions, spend, revenue_generated, roas`.

7. **Product rows** — extracted where `product_name` is non-null. Contains: `product_id, product_name, category, brand, price, mrp, margin_percentage, shelf_life_days, min_stock_level, max_stock_level`.

---

## Data Cleaning Methodology

**File:** `src/data_cleaning.py`

For each sub-table, the following validation checks are applied and reported (issues are flagged, never silently corrected):

| Check Type | Details |
|-----------|---------|
| Missing values | All key columns checked |
| Duplicate records | Primary key columns checked |
| Numeric range validation | ratings [1,5]; prices > 0; quantities > 0; delivery times |
| Date parsing & validation | Dates cast to datetime; `actual_delivery_time >= order_date` |
| Categorical validation | Sentinel/feedback/payment/delivery-status/segment/category values |
| Arithmetic consistency | `quantity × unit_price` vs `order_total` (see Data Quality section) |
| Inventory consistency | `damaged_stock <= stock_received` |
| Referential integrity | `feedback.order_id → orders`, `delivery.order_id → orders`, `orders.customer_id → customers` |

---

## Data Quality Issues Found

### 1. Order Total Mismatch (4,999 / 5,000 orders)
`order_total ≠ quantity × unit_price` for 4,999 of 5,000 orders.  
**Assessment:** Expected — `order_total` likely reflects the actual charged amount including applicable taxes, delivery fees, and discounts not separately captured in the dataset. Source values are preserved unchanged. This is flagged in the Orders & Revenue tab of the dashboard.

### 2. Damaged Stock > Stock Received (29,299 / 93,277 inventory records)
`damaged_stock > stock_received` in approximately 31.4% of inventory records.  
**Assessment:** Data quality issue in the source system (possibly incorrect entries or different measurement basis). Source values are preserved unchanged. Displayed as a warning in the Inventory tab.

---

## Analysis Methodology

**File:** `src/analysis.py`

All results are computed programmatically from the actual data — no hardcoded values. Key analytical functions:

- **Overview KPIs:** total orders, total revenue, avg order value, avg rating, on-time delivery %, avg delivery time, total ad spend, overall ROAS
- **Revenue:** monthly trend, by payment method, by store (top 20), by category, by product
- **Delivery:** status breakdown, delay reasons, time distribution, partner performance, delivery delay ↔ customer satisfaction correlation
- **Feedback:** rating distribution, sentiment distribution, avg rating by feedback category, sentiment trend over time
- **Customers:** segment breakdown, top areas, avg order value by segment, segment revenue contribution
- **Inventory:** stock received vs damaged trend over time, damage rate by category and product
- **Campaigns:** ROAS by channel, spend vs revenue, CTR & conversion rate by channel, ROAS by target audience, best/worst campaigns

---

## Key Findings

### Orders & Revenue
- **5,000 orders** totalling **₹1,10,09,309** with an average order value of **₹2,202**
- Order date range: March 2023 – November 2024
- **Dairy & Breakfast** leads in category revenue, followed by Household Care and Pet Care
- Payment methods are well distributed across Cash, UPI, Card, and Wallet

### Delivery Performance
- **69.4% of deliveries are On Time** — leaving 30.6% delayed
- Average delivery time: **4.4 minutes** (extremely fast — consistent with quick-commerce model)
- Most common delay reason: Traffic
- Delivery delays correlate negatively with customer ratings and positive sentiment

### Customer Feedback & Ratings
- Average rating: **3.34 / 5** — moderate satisfaction, room for improvement
- Sentiment split: Neutral 34.8%, Negative 32.8%, Positive 32.4% — a balanced but somewhat negative skew
- Delivery category receives the lowest average rating; App Experience also scores below average

### Marketing Campaigns
- Overall ROAS: **1.97x** (₹1 spend returns ~₹1.97)
- **Email** channel has the highest ROAS (2.05x); **App** has the lowest (1.92x)
- All channels are broadly profitable but margins are slim — campaigns should target higher-ROAS channels

### Inventory & Stock
- **Household Care** and **Personal Care** categories have the highest damage rates (~51–57%)
- **Pharmacy** and **Pet Care** have the lowest damage rates (~37%)
- Overall damage rate is significant — supply chain and packaging improvements are recommended for high-damage categories

### Customers
- Four segments: Premium, Regular, New, Inactive
- Geographic spread across many Indian cities

---

## Business Recommendations

1. **Delivery reliability:** With 30.6% delayed deliveries, investigate and address traffic congestion routing and partner allocation. Improving on-time rate directly correlates with higher ratings and positive sentiment.
2. **High-damage inventory:** Household Care and Personal Care categories suffer ~50%+ damage rates. Review supplier packaging standards and storage conditions for these categories.
3. **Marketing channel optimization:** Shift campaign budget toward Email (highest ROAS 2.05x) and away from App channel (lowest 1.92x). Overall ROAS of ~2x is acceptable but could be improved.
4. **Customer satisfaction:** Average rating of 3.34/5 is moderate. Since delivery performance is the top driver of negative feedback, addressing delivery delays will have the highest impact on ratings.
5. **Inactive customer re-engagement:** Target the Inactive segment with dedicated re-engagement campaigns; this segment currently contributes less revenue per customer than Premium/Regular.

---

## Dashboard Features

### Tabs
| Tab | Key Features |
|-----|-------------|
| Overview | 8 KPI cards, monthly revenue trend, delivery status pie, highlights |
| Orders & Revenue | Revenue trend, payment method, order value distribution, by-category chart, top stores, top products, consistency check |
| Delivery | Status breakdown, delay reasons, delivery time histogram, partner scatter, delay vs rating analysis |
| Feedback & Ratings | Rating distribution, sentiment pie, by-category rating, sentiment trend over time, rating table with icons |
| Marketing | ROAS by channel, CTR & conversion, ROAS by audience, spend vs revenue scatter, best/worst campaigns |
| Inventory | Stock trend, damage rate by category, top-damaged products, data quality warning |
| Customers | Segment breakdown, AOV by segment, top areas, segment revenue contribution |

### Sidebar Filters (applied globally)
- Date Range (order dates)
- Payment Method
- Product Category
- Customer Segment
- Campaign Channel

---

## Project Structure

```
project/
├── data/
│   ├── raw/                    # Original files (untouched)
│   │   ├── happy_merged.csv
│   │   ├── Category_Icons.xlsx
│   │   └── Rating_Icon.xlsx
│   └── processed/              # Split & cleaned sub-tables
│       ├── feedback.csv
│       ├── customers.csv
│       ├── delivery.csv
│       ├── orders.csv
│       ├── inventory.csv
│       ├── campaigns.csv
│       └── products.csv
├── src/
│   ├── data_splitting.py       # Un-merge the CSV into 7 sub-tables
│   ├── data_cleaning.py        # Validate and clean each sub-table
│   ├── analysis.py             # Business analytics functions
│   └── visualization.py        # Plotly chart builders
├── app.py                      # Streamlit dashboard (entry point)
├── run_pipeline.py             # Standalone: run full data pipeline
├── requirements.txt
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.10 or later
- pip

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## How to Run

### Step 1 — Run the Data Pipeline

This splits `happy_merged.csv` into 7 sub-tables, cleans, and validates them:

```bash
python run_pipeline.py
```

Output goes to `data/processed/`. A log file `pipeline.log` is also written.

> **Note:** The Streamlit app automatically runs the pipeline on first launch if the processed files are missing. You can skip this step if you just want to run the dashboard directly.

### Step 2 — Launch the Dashboard

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501` in your browser.

---

## Reproducing the Analysis

The entire pipeline is reproducible from `happy_merged.csv`:

1. `data_splitting.py` — deterministic, key-column-based row assignment
2. `data_cleaning.py` — type casting and validation; no values are altered
3. `analysis.py` — all metrics computed from the cleaned sub-tables
4. `app.py` — fetches live computed values; no hardcoded results

Re-run `python run_pipeline.py` at any time to regenerate from scratch.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| streamlit >= 1.30.0 | Web dashboard framework |
| pandas >= 2.0.0 | Data processing |
| plotly >= 5.18.0 | Interactive visualizations |
| numpy >= 1.26.0 | Numeric operations |
| openpyxl >= 3.1.0 | Read icon Excel files |

---

## Assumptions

1. **`happy_merged.csv` is the sole source of truth.** No external reference or pre-stated "expected results" were used to validate analysis outputs.
2. **Orders split across two row types.** Validated by non-null co-occurrence patterns; the join on `order_id` matches all 5,000 records perfectly.
3. **Order total mismatch.** `order_total ≠ quantity × unit_price` for 99.98% of orders. Assumed to reflect taxes/fees/discounts — source values preserved.
4. **Damaged stock anomaly.** ~31% of inventory records have `damaged_stock > stock_received`. Treated as a source data quality issue — not corrected.
5. **Icon files present and used.** Both `Category_Icons.xlsx` and `Rating_Icon.xlsx` are present with usable URL mappings. They are used non-critically (missing gracefully if unavailable).
6. **Inventory date formats.** The `date` column in inventory contains mixed formats (e.g., `17-03-2023` and `Sep-24`). Parsed with `format="mixed"` using pandas.
7. **Delivery time in minutes.** Negative values exist (arrived early relative to promise). These are not treated as errors — they represent early deliveries.

---

## Known Limitations

- The `orders` table has only one product item per order (`order_id` is unique in item rows). Multi-item order analysis is therefore not possible from this dataset.
- The `delivery` sub-table (Type A) does not include `customer_id` — delivery-to-customer analytics require joining through the order header rows.
- The `inventory` date range spans Jan 2023 – Sep 2024 with mixed formats; some months in the chart may appear out of order for non-standard date strings — handled by pandas mixed-format parsing.
- Store analysis is limited because `store_id` values are numeric IDs with no store name or location metadata in the dataset.
