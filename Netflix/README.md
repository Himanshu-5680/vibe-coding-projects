# Netflix Content Strategy & Catalog Analytics Platform

## Project Overview
Single-file Streamlit capstone platform analyzing Netflix's global catalog using the Kaggle dataset `shivamb/netflix-shows`. The application follows a five-level business intelligence hierarchy: executive KPIs, content velocity, portfolio drivers, risks and whitespace, and strategic actions.

## Tech Stack
- Frontend: Streamlit
- Data preparation: pandas and NumPy
- Visualization: Plotly
- Data source: Kaggle via `kagglehub`
- Report export: `python-docx`

## Quick Start Guide

### Prerequisites
- Python 3.10+
- Kaggle account and API credentials configured for `kagglehub`

### Installation
```bash
pip install -r requirements.txt
```

### Running the App
```bash
streamlit run app.py
```

## Kaggle Dataset
Dataset link: https://www.kaggle.com/datasets/shivamb/netflix-shows

The app downloads the dataset automatically on first run through `kagglehub`.

## Single-File Design
All logic is consolidated in `app.py`:
- Data ingestion and caching
- Data validation and quality reporting
- KPI calculation engine
- 5-level BI analysis
- Plotly visualization layer
- Streamlit dashboard UI
- Word report generation

## 5-Level BI Framework
1. KPIs: What is happening?
2. Trends: Direction of movement?
3. Drivers: Why is it happening?
4. Risks & Opportunities: What could go wrong/right?
5. Actions: What should we do?

## Dashboard Features
- Five-column executive KPI layout: total titles, movies, TV shows, global reach, and content diversity
- Year-over-year acquisition trajectory and monthly seasonality
- Top genres, movie runtime histogram, TV season-retention donut, and audience maturity segmentation
- Catalog aging, single-season churn, maturity skew, APAC/LATAM whitespace, and strategic action matrix
- Comprehensive multi-page Word report generated dynamically in the Report tab

## Data Quality Assurance
- Missing value detection and reporting
- Duplicate checks
- Outlier and anomaly screening
- Type and date validation
- Transparent calculation logic derived from the actual dataset

## Important Note on Rating Data
The Netflix dataset's `rating` field is a categorical maturity label such as `TV-MA`, `TV-14`, `PG-13`, or `TV-Y`. The application does not convert these labels into a fake quality score or IMDb-style rating. It groups them into audience segments for portfolio analysis.

## Assumptions & Limitations
- The analytics use the Kaggle dataset as the source of truth.
- Rating-related metrics are based on audience maturity segments.
- Geographic and genre analysis are derived from country and genre fields in the catalog.

## Project Structure
- `app.py` — complete single-file dashboard
- `requirements.txt` — environment dependencies
- `README.md` — documentation

## Report Generation
The app includes a `Download Report (.docx)` action that builds a project report on demand using the current filtered dataset and aggregated metrics.

## References
- Kaggle dataset: shivamb/netflix-shows
- Streamlit documentation: https://streamlit.io
- Plotly documentation: https://plotly.com/python
