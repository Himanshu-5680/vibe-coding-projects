# 🛒 Supermarket Sales Intelligence Dashboard

> **A fully AI-orchestrated data analytics project** — built end-to-end using structured prompting with IBM Bob, demonstrating how modern Vibe Coding turns business questions into production-ready dashboards without writing a single line of syntax manually.

---

## ⚡ The Vibe Coding Approach

This project was not built by typing code — it was **orchestrated**.

Vibe Coding is a modern development paradigm where the engineer acts as an **architect and director**, designing the solution logic, data flow, and business requirements in natural language, and delegating the implementation to an AI assistant. Every file in this repository — from the data pipeline to the Streamlit UI — was generated through structured, intent-driven prompts to **IBM Bob**, IBM's AI software engineering assistant.

### How it worked

| Phase | Human Role | IBM Bob's Role |
|---|---|---|
| **Problem framing** | Defined business questions and KPIs to answer | — |
| **Architecture** | Specified the two-module design (`analysis.py` + `app.py`) | Scaffolded both files from scratch |
| **Data pipeline** | Described the cleaning requirements and Sales formula | Wrote the full 10-step pandas pipeline |
| **Visualisations** | Specified chart types, dark theme, and Plotly constraints | Generated all Plotly figures with correct modern syntax |
| **UI/UX** | Defined the dark theme rules, tab structure, and metric layout | Built the complete Streamlit dashboard with custom CSS |
| **Debugging** | Identified the `TypeError` from dict unpacking collision | Diagnosed root cause and refactored all 11 affected chart calls |
| **Reporting** | Requested a 12-slide PowerPoint for the business team | Generated the full `.pptx` with data-accurate content |

The result is a fully functional, production-ready analytics dashboard — delivered through **intent, not syntax**.

---

## 💼 Business Understanding

### The Problem

Retail supermarket chains with multiple branches face a common challenge: **sales data exists, but insight does not**. Managers lack a fast, visual way to answer questions like:

- Which branch is generating the most revenue — and why?
- Which product categories drive the majority of sales?
- Are customers paying digitally or with cash — and does it matter?
- When are peak sales months, and how do we plan for them?
- Which customer segment (Member vs Normal) is more valuable?

### The Solution

This dashboard transforms 500 raw transaction records into a **six-tab interactive analytics hub** that answers every one of those questions in real time, with filters for branch, category, gender, and customer type applied globally across all charts.

---

## 📊 Data Understanding

| Attribute | Detail |
|---|---|
| **Source File** | `SUPER MARKET DATA.xlsx` |
| **Sheet** | `supermarket_sales_500_rows` |
| **Records** | 500 transactions × 13 columns |
| **Date Range** | January 2026 – July 2026 |
| **Branches** | A (Jaipur), B (Delhi), C (Mumbai), D (Bengaluru) |
| **Product Categories** | Bakery, Beverages, Dairy, Fruits, Grocery, Personal Care, Snacks, Vegetables |
| **Payment Methods** | UPI, Net Banking, Card, Cash |

### Column Schema

| Column | Type | Description |
|---|---|---|
| `Invoice ID` | String | Unique transaction identifier |
| `Date` | Date | Transaction date |
| `Branch` | Category | Store branch (A / B / C / D) |
| `City` | Category | Branch city |
| `Customer Type` | Category | Member or Normal |
| `Gender` | Category | Male or Female |
| `Product` | String | Product name |
| `Category` | Category | Product category |
| `Quantity` | Numeric | Units purchased |
| `Unit Price` | Numeric | Price per unit (₹) |
| `Payment` | Category | Payment method |
| `Rating` | Numeric | Customer satisfaction score (1–10) |
| `Sales` | Numeric | **Derived:** `Quantity × Unit Price` |

### Data Cleaning Pipeline (10 Steps)

1. Load Excel via `pandas` with `openpyxl` engine
2. Standardise column names (strip whitespace)
3. Drop fully empty rows and columns
4. Parse `Date` to `datetime` (errors coerced)
5. Coerce `Quantity`, `Unit Price`, `Rating` to numeric
6. Drop rows missing critical fields (`Quantity`, `Unit Price`)
7. Fill remaining categorical `NaN` values with `"Unknown"`
8. Strip leading/trailing whitespace from all text fields
9. **Recalculate** `Sales = Quantity × Unit Price` (guarantees consistency)
10. Derive `Month` (YYYY-MM) and `Day` (day-of-week) features

**Result:** 500 clean records · 0 missing values · 0 duplicates

### Key Metrics (from the dataset)

| KPI | Value |
|---|---|
| 💰 Total Revenue | ₹2,44,411 |
| 🧾 Total Transactions | 500 |
| 📊 Avg Sale per Transaction | ₹488.82 |
| ⭐ Avg Customer Rating | 3.99 / 10 |
| 📦 Total Units Sold | 2,768 |
| 🏆 Top Branch | C — Mumbai (₹72,469) |
| 📦 Top Category | Beverages (₹56,108 · 22.96%) |
| 🥇 Top Product | Cheese (₹27,906) |
| 💳 Top Payment Method | UPI (₹67,910 · 27.8%) |
| 📅 Peak Month | April 2026 (₹52,570) |

---

## 🛠️ Technologies

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core programming language |
| **Pandas** | Data loading, cleaning, and aggregation |
| **NumPy** | Numeric operations |
| **Plotly 5.x** | Interactive business charts (modern syntax — no deprecated properties) |
| **Streamlit** | Dark-theme interactive web dashboard |
| **OpenPyXL** | Excel file reading engine |

---

## 🗂️ Project Structure

```
supermarket-sales-dashboard/
│
├── SUPER MARKET DATA.xlsx        # Source dataset (500 transactions)
│
├── analysis.py                   # Data pipeline & aggregation module
│   ├── load_data()               # Load, clean, derive features
│   ├── summary_stats()           # Top-level KPIs
│   ├── sales_by_branch()         # Branch performance table
│   ├── sales_by_category()       # Category revenue breakdown
│   ├── sales_by_product()        # Product-level ranking
│   ├── sales_by_payment()        # Payment method split
│   ├── sales_by_gender()         # Gender demographic split
│   ├── sales_by_customer_type()  # Member vs Normal
│   ├── monthly_trend()           # Month-over-month revenue
│   └── top_products_by_branch()  # Product × Branch matrix
│
├── app.py                        # Streamlit dark-theme dashboard
│   ├── Tab 1: Branch Performance
│   ├── Tab 2: Product & Category
│   ├── Tab 3: Payment & Demographics
│   ├── Tab 4: Time Trends
│   ├── Tab 5: Product × Branch Heatmap
│   └── Tab 6: Key Insights + Raw Data Explorer
│
├── Supermarket_Sales_Report.pptx # 12-slide PowerPoint business report
│
├── requirements.txt              # Pinned Python dependencies
└── README.md                     # This file
```

---

## 🚀 Setup & Execution

### Prerequisites

- Python 3.10 or higher
- `pip` package manager

### 1 — Clone the Repository

```bash
git clone https://github.com/your-username/supermarket-sales-dashboard.git
cd supermarket-sales-dashboard
```

### 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

**`requirements.txt` contents:**
```
streamlit>=1.32.0
pandas>=2.0.0
openpyxl>=3.1.0
plotly>=5.18.0
numpy>=1.26.0
```

### 3 — Run the Dashboard

```bash
streamlit run app.py
```

The dashboard opens automatically at **`http://localhost:8501`**

### 4 — Using the Dashboard

- Use the **sidebar filters** (Branch, Category, Gender, Customer Type) to slice all charts simultaneously
- Navigate through **6 tabs** to explore different analytical views
- Use the **Raw Data Explorer** on the Insights tab to search and filter transaction-level records

---

## 🏗️ Architecture

```
SUPER MARKET DATA.xlsx
        │
        ▼
  analysis.py  ◄── Pure data layer (no UI)
  (load · clean · aggregate)
        │
        ▼
    app.py  ◄── Presentation layer (Streamlit + Plotly)
  (render · filter · visualise)
```

The two-module separation ensures:
- `analysis.py` is independently testable and reusable
- `app.py` contains zero data logic — only rendering
- Adding new charts never requires touching the data pipeline

---

## 💡 Key Business Insights

1. **Branch C (Mumbai)** generates 38.5% more revenue than Branch A with only 36% more transactions — higher basket sizes drive this gap
2. **Beverages + Personal Care** together account for 42% of total revenue from just 30% of transactions — the highest-value category pair
3. **UPI + Net Banking** = 54.5% of revenue — over half of all sales are now fully digital
4. **Member customers** generate 58.5% of revenue — the loyalty programme is the most important retention lever
5. **April 2026** is the peak month at ₹52,570 — 75% above the February trough; seasonal planning is critical
6. **Bakery** generates only 2.7% of revenue from 28 transactions — the largest untapped growth opportunity

---

## 📋 Business Recommendations

| # | Recommendation | Priority |
|---|---|---|
| R1 | Scale Branch C operational practices to Branches A and D | 🔴 High |
| R2 | Allocate 30–35% shelf space and budget to Beverages & Personal Care | 🔴 High |
| R3 | Launch a February recovery campaign (UPI cashback / member double-points) | 🟡 Medium |
| R4 | Implement frictionless at-checkout membership sign-up flow | 🟡 Medium |
| R5 | Fix service quality at Branch A — target rating 4.5+ within 60 days | 🔴 High |
| R6 | Pilot fresh bakery section or Beverages + Bakery combo promotion | 🟢 Low |

---

## 📄 PowerPoint Report

A 12-slide business presentation (`Supermarket_Sales_Report.pptx`) is included in the repository, covering:

- Dataset overview and column schema
- Data cleaning steps and outcomes
- KPI summary with all 5 key metrics
- Branch performance ranked table and analysis
- Product & category revenue breakdown
- Payment methods and demographic analysis
- Monthly sales trends with seasonal commentary
- Cross-analysis: Branch vs Category heatmap findings
- 8 key business insights
- 6 actionable recommendations with next steps

---

## 👤 Author
**Himanshu Pathak** — Data Analyst & Vibe Coder  
**Built with:** IBM Bob (AI Software Engineering Assistant)

**Approach:** Vibe Coding — AI-orchestrated, intent-driven development

---

*This project demonstrates that the future of software engineering is not about typing faster — it is about thinking clearer.*
