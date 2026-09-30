import io
import warnings
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import kagglehub
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

warnings.filterwarnings("ignore")


ADULT_RATINGS = {"TV-MA", "R", "NC-17"}
TEEN_RATINGS = {"TV-14", "PG-13"}
KIDS_RATINGS = {"TV-Y", "TV-Y7", "TV-G", "G", "PG", "TV-PG"}
NOT_RATED_RATINGS = {"NR", "UR", "UNRATED", "NOT RATED"}


def map_rating_segment(value):
    if pd.isna(value):
        return "Not Rated"
    rating = str(value).strip().upper()
    if rating in ADULT_RATINGS:
        return "Adults (18+)"
    if rating in TEEN_RATINGS:
        return "Teens (13-17)"
    if rating in KIDS_RATINGS:
        return "Kids & Family (<13)"
    if rating in NOT_RATED_RATINGS or rating == "NAN":
        return "Not Rated"
    return "Not Rated"


@st.cache_resource
def load_dataset_path():
    try:
        return kagglehub.dataset_download("shivamb/netflix-shows")
    except Exception as exc:
        st.error(f"Dataset download failed: {exc}")
        return None


@st.cache_data
def load_and_prepare_data():
    dataset_path = load_dataset_path()
    if dataset_path is None:
        return pd.DataFrame(), {"status": "download_failed"}

    csv_candidates = list(Path(dataset_path).glob("*.csv"))
    csv_file = next((p for p in csv_candidates if p.name == "netflix_titles.csv"), csv_candidates[0] if csv_candidates else None)

    if csv_file is None:
        return pd.DataFrame(), {"status": "not_found"}

    df = pd.read_csv(csv_file)
    validation_report = validate_dataset(df)
    cleaned = clean_dataframe(df)
    return cleaned, validation_report


def clean_dataframe(df):
    cleaned = df.copy()

    for col in ["show_id", "type", "title", "director", "cast", "country", "date_added", "release_year", "rating", "duration", "listed_in", "description"]:
        if col not in cleaned.columns:
            cleaned[col] = None

    cleaned["type"] = cleaned["type"].fillna("Unknown").astype(str).str.strip().str.title()
    cleaned["type"] = cleaned["type"].replace({"Tv Show": "TV Show", "Movie": "Movie"})

    cleaned["title"] = cleaned["title"].fillna("Unknown").astype(str)
    cleaned["country"] = cleaned["country"].fillna("Unknown").astype(str)
    cleaned["listed_in"] = cleaned["listed_in"].fillna("Unknown").astype(str)
    cleaned["rating"] = cleaned["rating"].fillna("Not Rated").astype(str)
    cleaned["date_added"] = pd.to_datetime(cleaned["date_added"], errors="coerce")
    cleaned["release_year"] = pd.to_numeric(cleaned["release_year"], errors="coerce")
    duration_values = cleaned["duration"].astype(str).str.extract(r"(\d+)", expand=False)
    cleaned["duration_minutes"] = pd.to_numeric(duration_values.where(cleaned["type"].eq("Movie")), errors="coerce")
    cleaned["season_count"] = pd.to_numeric(duration_values.where(cleaned["type"].eq("TV Show")), errors="coerce")
    cleaned["rating_segment"] = cleaned["rating"].apply(map_rating_segment)

    return cleaned


def validate_dataset(df):
    report = {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "missing": {},
        "duplicates": int(df.duplicated().sum()),
        "anomalies": {},
        "status": "ok",
    }

    missing = df.isna().mean().sort_values(ascending=False)
    report["missing"] = {col: round(float(val * 100), 2) for col, val in missing.items() if val > 0}

    if report["duplicates"] > 0:
        report["status"] = "warnings"
    if report["missing"]:
        report["status"] = "warnings"

    release_years = pd.to_numeric(df.get("release_year", pd.Series([None] * len(df))), errors="coerce")
    future_years = int((release_years > pd.Timestamp.today().year).sum())
    if future_years > 0:
        report["status"] = "warnings"

    rating_values = df.get("rating", pd.Series(["Not Rated"] * len(df), index=df.index)).fillna("Not Rated").astype(str)
    allowed_ratings = ADULT_RATINGS | TEEN_RATINGS | KIDS_RATINGS | NOT_RATED_RATINGS | {"NOT RATED", "UNRATED", "NAN"}
    report["anomalies"] = {
        "future_release_years": future_years,
        "unknown_rating_values": int((~rating_values.astype(str).str.upper().isin(allowed_ratings)).sum()),
        "duplicate_rows": report["duplicates"],
    }
    return report


def flatten_list_values(series):
    values = []
    for item in series.dropna():
        parts = [p.strip() for p in str(item).split(",")]
        for p in parts:
            if p and p != "Unknown" and p.lower() != "nan":
                values.append(p)
    return values


def calculate_kpis(df):
    if df.empty:
        return {
            "total_shows": 0,
            "titles_added_12m": 0,
            "geographic_reach": 0,
            "genre_diversity": 0,
            "movie_count": 0,
            "tv_show_count": 0,
            "movies_share": 0.0,
            "tv_share": 0.0,
            "maturity_distribution": {"Adults (18+)": 0, "Teens (13-17)": 0, "Kids & Family (<13)": 0, "Not Rated": 0},
            "catalog_growth_yoy": 0.0,
        }

    total_shows = int(len(df))
    added_12m = int(df["date_added"].dropna().ge(pd.Timestamp.today() - pd.DateOffset(months=12)).sum())
    geographic_reach = len(set(flatten_list_values(df["country"])))
    genre_diversity = len(set(flatten_list_values(df["listed_in"])))

    type_counts = df["type"].value_counts(dropna=False)
    movie_count = int(type_counts.get("Movie", 0))
    tv_count = int(type_counts.get("TV Show", 0))
    movies_share = round((movie_count / total_shows) * 100, 2) if total_shows else 0.0
    tv_share = round((tv_count / total_shows) * 100, 2) if total_shows else 0.0

    year_counts = df.dropna(subset=["date_added"]).copy()
    year_counts["year"] = year_counts["date_added"].dt.year
    year_counts = year_counts.groupby("year").size().reset_index(name="count")
    if len(year_counts) >= 2:
        current_year = year_counts.iloc[-1]["count"]
        prev_year = year_counts.iloc[-2]["count"] if len(year_counts) > 1 else current_year
        growth_yoy = round(((current_year - prev_year) / prev_year * 100), 2) if prev_year else 0.0
    else:
        growth_yoy = 0.0

    maturity_distribution = {
        "Adults (18+)": int((df["rating_segment"] == "Adults (18+)").sum()),
        "Teens (13-17)": int((df["rating_segment"] == "Teens (13-17)").sum()),
        "Kids & Family (<13)": int((df["rating_segment"] == "Kids & Family (<13)").sum()),
        "Not Rated": int((df["rating_segment"] == "Not Rated").sum()),
    }

    return {
        "total_shows": total_shows,
        "titles_added_12m": added_12m,
        "geographic_reach": geographic_reach,
        "genre_diversity": genre_diversity,
        "movie_count": movie_count,
        "tv_show_count": tv_count,
        "movies_share": movies_share,
        "tv_share": tv_share,
        "maturity_distribution": maturity_distribution,
        "catalog_growth_yoy": growth_yoy,
    }


@st.cache_data
def build_trend_data(df):
    trend_df = df.dropna(subset=["date_added"]).copy()
    if trend_df.empty:
        return {"monthly_additions": pd.DataFrame(), "yearly_additions": pd.DataFrame()}

    trend_df["Month"] = trend_df["date_added"].dt.to_period("M").astype(str)
    monthly = trend_df.groupby("Month").size().reset_index(name="Titles Added")

    trend_df["Year"] = trend_df["date_added"].dt.year
    yearly = trend_df.groupby("Year").size().reset_index(name="Titles Added")

    return {"monthly_additions": monthly, "yearly_additions": yearly}


@st.cache_data
def build_driver_data(df):
    if df.empty:
        return {"top_genres": pd.DataFrame(), "movie_runtime": pd.DataFrame(), "tv_seasons": pd.DataFrame(), "maturity_distribution": pd.DataFrame()}

    genre_rows = []
    for item in df["listed_in"].dropna().astype(str):
        for genre in [g.strip() for g in item.split(",") if g.strip() and g.strip() != "Unknown"]:
            genre_rows.append(genre)

    top_genres = pd.Series(genre_rows).value_counts().reset_index()
    top_genres.columns = ["Genre", "Title Count"]
    top_genres = top_genres.head(10).sort_values("Title Count", ascending=False)

    movie_runtime = df[df["type"] == "Movie"].copy()
    movie_runtime = movie_runtime.dropna(subset=["duration_minutes"])
    movie_runtime = movie_runtime[["duration_minutes"]].rename(columns={"duration_minutes": "Runtime Minutes"})

    tv_seasons = df[df["type"] == "TV Show"].copy()
    tv_seasons["season_bucket"] = tv_seasons["season_count"].apply(lambda x: "1 Season" if x <= 1 else "Multi-Season")
    tv_seasons = tv_seasons["season_bucket"].value_counts().reset_index()
    tv_seasons.columns = ["Season Structure", "Count"]

    maturity_distribution = df["rating_segment"].value_counts().reset_index()
    maturity_distribution.columns = ["Audience Segment", "Count"]

    return {
        "top_genres": top_genres,
        "movie_runtime": movie_runtime,
        "tv_seasons": tv_seasons,
        "maturity_distribution": maturity_distribution,
    }


@st.cache_data
def build_risk_opportunity_data(df):
    risks = []
    opportunities = []

    if df.empty:
        return risks, opportunities

    pre_2015_share = (df["release_year"].dropna() < 2015).mean() * 100 if df["release_year"].notna().any() else 0.0
    if pre_2015_share >= 25:
        risks.append({
            "Risk": "Catalog Aging",
            "Metric": f"{pre_2015_share:.1f}% of catalog pre-2015",
            "Severity": "High",
            "Impact": "Older titles risk weaker relevance and lower discovery velocity.",
            "Mitigation": "Refresh library mix with newer originals and franchise reactivation."
        })

    tv_df = df[df["type"] == "TV Show"].copy()
    if not tv_df.empty:
        single_season_share = (tv_df["season_count"].fillna(0).le(1).mean()) * 100
        if single_season_share > 65:
            risks.append({
                "Risk": "Single-Season TV Churn",
                "Metric": f"{single_season_share:.1f}% of TV shows have 1 season",
                "Severity": "High",
                "Impact": "Lower binge-watch retention and weaker episodic subscriber stickiness.",
                "Mitigation": "Prioritize multi-season renewal and spin-off strategy."
            })

    adult_share = (df["rating_segment"] == "Adults (18+)").mean() * 100 if not df.empty else 0.0
    if adult_share > 45:
        risks.append({
            "Risk": "Heavy Mature Content Skew",
            "Metric": f"{adult_share:.1f}% of catalog is Adults (18+)",
            "Severity": "Medium",
            "Impact": "Restricts family co-viewing and broader household acquisition potential.",
            "Mitigation": "Blend in more family-friendly and teen-skewed programming."
        })

    country_counts = pd.Series(flatten_list_values(df["country"])).value_counts()
    region_map = {
        "India": "APAC",
        "South Korea": "APAC",
        "Japan": "APAC",
        "Mexico": "LATAM",
        "Brazil": "LATAM",
        "Argentina": "LATAM",
        "United Kingdom": "EMEA",
        "France": "EMEA",
        "Germany": "EMEA",
        "Canada": "North America",
        "United States": "North America",
    }
    regional = pd.Series(country_counts.index).map(region_map).fillna("Other")
    region_counts = pd.DataFrame({"Country": country_counts.index, "Shows": country_counts.values})
    region_counts["Region"] = region_counts["Country"].map(region_map).fillna("Other")
    region_totals = region_counts.groupby("Region")["Shows"].sum().sort_values(ascending=False)
    if "APAC" in region_totals.index:
        opportunities.append({
            "Opportunity": "APAC Growth White Space",
            "Metric": f"APAC catalog share is {region_totals.get('APAC', 0)} titles",
            "Potential": "High",
            "Action": "Scale India and South Korea local-language originals for subscriber acquisition."
        })
    if "LATAM" in region_totals.index:
        opportunities.append({
            "Opportunity": "LATAM Expansion",
            "Metric": f"LATAM catalog share is {region_totals.get('LATAM', 0)} titles",
            "Potential": "High",
            "Action": "Increase Spanish-language programming and regional co-productions."
        })

    genre_counts = pd.Series(flatten_list_values(df["listed_in"])).value_counts()
    low_share = genre_counts[genre_counts / genre_counts.sum() < 0.05]
    if not low_share.empty:
        example = low_share.head(1)
        opportunities.append({
            "Opportunity": "High-Demand White Space",
            "Metric": f"{example.index[0]} share is {((example.iloc[0] / genre_counts.sum()) * 100):.1f}%",
            "Potential": "Medium",
            "Action": "Increase documentary and anime-specific acquisition pipelines."
        })

    return risks, opportunities


@st.cache_data
def generate_recommendations(df, kpis, trends, drivers, risks, opportunities):
    recommendations = []

    if df.empty:
        return recommendations

    genre_counts = pd.Series(flatten_list_values(df["listed_in"])).value_counts()
    top_genre = genre_counts.index[0]
    top_genre_count = int(genre_counts.iloc[0])

    us_canada = df[df["country"].fillna("").str.contains("United States|Canada", case=False, na=False)]
    us_canada_share = (len(us_canada) / len(df)) * 100 if len(df) else 0.0

    tv_df = df[df["type"] == "TV Show"].copy()
    single_season_share = (tv_df["season_count"].fillna(0).le(1).mean() * 100) if not tv_df.empty else 0.0

    recommendations.append({
        "Priority": 1,
        "Theme": "Catalog Refresh & Licensing Retention",
        "Recommendation": f"For US/Canada, prioritize catalog refresh and licensing retention instead of expansion; current US/Canada share is {us_canada_share:.1f}% of the library and requires renewal economics, not broad market growth.",
        "Impact": "High"
    })
    recommendations.append({
        "Priority": 2,
        "Theme": "International Expansion",
        "Recommendation": "Allocate capital to India, South Korea, and EMEA for local-language originals and regional subscriber acquisition, especially where catalog depth is still modest.",
        "Impact": "High"
    })
    recommendations.append({
        "Priority": 3,
        "Theme": "TV Show Strategy",
        "Recommendation": f"Invest in multi-season renewals because {single_season_share:.1f}% of TV titles are only 1 season; retention improves materially with proven seasonal franchises.",
        "Impact": "High"
    })
    recommendations.append({
        "Priority": 4,
        "Theme": "Genre Investment",
        "Recommendation": f"Grow {top_genre} acquisitions further as it is the largest volume genre in the current library ({top_genre_count} titles), while balancing documentary and anime opportunities.",
        "Impact": "Medium"
    })

    return recommendations


def build_maturity_chart(df):
    if df.empty:
        return px.bar(pd.DataFrame({"Segment": [], "Count": []}), x="Segment", y="Count")

    freq = df["rating_segment"].value_counts().reindex(["Adults (18+)", "Teens (13-17)", "Kids & Family (<13)", "Not Rated"], fill_value=0)
    chart_df = pd.DataFrame({"Segment": freq.index, "Count": freq.values})
    fig = px.bar(chart_df, x="Segment", y="Count", color="Segment", title="Audience maturity distribution")
    fig.update_layout(template="plotly_white", showlegend=False)
    return fig


def build_top_genres_chart(df):
    rows = []
    for item in df["listed_in"].dropna().astype(str):
        for genre in [g.strip() for g in item.split(",") if g.strip() and g.strip() != "Unknown"]:
            rows.append(genre)
    chart_df = pd.Series(rows).value_counts().head(10).reset_index()
    chart_df.columns = ["Genre", "Title Count"]
    chart_df = chart_df.sort_values("Title Count", ascending=False)
    fig = px.bar(chart_df, x="Title Count", y="Genre", orientation="h", title="Top 10 genres by catalog count")
    fig.update_layout(template="plotly_white", showlegend=False)
    return fig


def build_duration_chart(df):
    movie_runtime = df[(df["type"] == "Movie") & df["duration_minutes"].notna()][["duration_minutes"]].copy()
    if not movie_runtime.empty:
        fig1 = px.histogram(movie_runtime, x="duration_minutes", nbins=20, title="Movie runtime distribution (minutes)")
        fig1.update_layout(template="plotly_white")
        return fig1

    tv_df = df[df["type"] == "TV Show"].copy()
    if not tv_df.empty:
        tv_df["season_bucket"] = tv_df["season_count"].apply(lambda x: "1 Season" if pd.notna(x) and x <= 1 else "Multi-Season")
        count_df = tv_df["season_bucket"].value_counts().reset_index()
        count_df.columns = ["Season Structure", "Count"]
        fig = px.bar(count_df, x="Season Structure", y="Count", title="TV season structure")
        fig.update_layout(template="plotly_white")
        return fig

    return px.bar(pd.DataFrame({"Value": [0]}), x="Value", y="Value")


def build_acquisition_trend(df):
    chart_df = df.dropna(subset=["date_added"]).copy()
    chart_df["Year"] = chart_df["date_added"].dt.year
    chart_df = chart_df.groupby("Year").size().reset_index(name="Titles Added")
    fig = px.line(chart_df, x="Year", y="Titles Added", markers=True, title="Content acquisition trajectory")
    fig.update_layout(template="plotly_white")
    return fig


def _shade_cell(cell, fill="E8EEF7"):
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def _add_report_table(doc, headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = str(header)
        _shade_cell(table.rows[0].cells[index], "17365D")
        for run in table.rows[0].cells[index].paragraphs[0].runs:
            run.font.bold = True
            run.font.color.rgb = __import__("docx").shared.RGBColor(255, 255, 255)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = str(value)
    doc.add_paragraph()
    return table


def _add_visual_placeholder(doc, text):
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    _shade_cell(cell, "D9EAF7")
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.bold = True
    run.font.size = Pt(11)
    doc.add_paragraph()


def generate_project_report(kpis, validation_report, recommendations, df):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("NETFLIX CONTENT STRATEGY & CATALOG ANALYTICS PLATFORM").bold = True
    title.runs[0].font.size = Pt(22)
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.add_run("A Business Intelligence Study on Catalog Velocity, Audience Maturity Demographics, and International Growth Whitespaces").italic = True
    for line in [
        "Prepared By: Himanshu Pathak",
        "Internship: IBM SkillsBuild Data Analytics with AI Internship 2026 (in collaboration with BharatCares / CSRBOX)",
        "Date: September 2026",
    ]:
        paragraph = doc.add_paragraph(line)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    doc.add_heading("Certificate of Originality", level=1)
    doc.add_paragraph("I declare that this project represents my independent analytical work on the Kaggle Netflix multi-attribute catalog dataset. The data preparation, metric definitions, visual analysis, strategic interpretation, and report generation were developed for this capstone submission. External libraries and references are acknowledged in the references section.")
    doc.add_heading("Acknowledgments", level=1)
    doc.add_paragraph("I acknowledge IBM SkillsBuild for the learning framework, BharatCares and CSRBOX for the internship context, mentors Kartik Hooda and Himanshu Souda for their guidance, and the open-source contributors whose tools enable reproducible data analysis.")

    doc.add_heading("Table of Contents", level=1)
    for item in [
        "Executive Summary", "1. Introduction & OTT Streaming Context", "2. Internship Framework & BI Mindset",
        "3. Core KPI Framework Matrix", "4. Dataset Architecture & Data Quality Audit",
        "5. Analytical Deep-Dive & Findings", "6. Visual Evidence Placeholders",
        "7. Strategic Recommendations & Prioritized Action Matrix", "8. Technical Learning Outcomes & References",
    ]:
        doc.add_paragraph(item, style="List Number")

    doc.add_heading("Executive Summary", level=1)
    tv_df = df[df["type"] == "TV Show"]
    single_season_share = (tv_df["season_count"].eq(1).mean() * 100) if not tv_df.empty else 0.0
    doc.add_paragraph(f"The current Kaggle snapshot contains {kpis['total_shows']:,} titles across {kpis['geographic_reach']} countries and {kpis['genre_diversity']} genres. Movies account for {kpis['movies_share']:.1f}% of the catalog and TV shows account for {kpis['tv_share']:.1f}%. Among TV shows, {single_season_share:.1f}% have one season, indicating a material renewal and retention opportunity. The US and Canada remain the core mature-market portfolio, while India, South Korea, EMEA, and LATAM provide localization and whitespace opportunities.")
    doc.add_paragraph("Metrics are calculated dynamically from the downloaded source snapshot. The dataset's rating field is treated as a categorical audience maturity label, never as an IMDb-style quality score.")

    doc.add_heading("1. Introduction & OTT Streaming Context", level=1)
    doc.add_paragraph("Subscription streaming economics depend on a portfolio that acquires subscribers, supports ongoing engagement, and limits churn. Content acquisition must therefore be evaluated alongside renewal depth, audience breadth, regional relevance, and catalog freshness. This platform translates title-level metadata into an executive decision system for content strategy.")
    doc.add_paragraph("The analysis distinguishes catalog supply from audience quality. Genre, country, runtime, season count, release year, addition date, and maturity labels describe portfolio structure; they do not independently measure viewing hours, completion, or subscriber lifetime value.")

    doc.add_heading("2. Internship Framework & Business Intelligence Mindset", level=1)
    doc.add_paragraph("The project follows a five-level BI hierarchy: raw data becomes validated information; descriptive KPIs establish what exists; time trends show how the portfolio changes; driver analysis explains structural composition; risk and whitespace analysis identifies management concerns; and strategic actions convert evidence into decisions.")
    _add_report_table(doc, ["BI Level", "Management Question", "Platform Output"], [
        ["1. Executive Overview", "What is the portfolio position?", "Title count, mix, reach, diversity"],
        ["2. Trends", "How is content velocity changing?", "Yearly trajectory and monthly seasonality"],
        ["3. Drivers", "What explains portfolio shape?", "Genres, runtime, seasons, maturity"],
        ["4. Risks & Whitespace", "Where is exposure or opportunity?", "Aging, churn, skew, regions"],
        ["5. Actions", "What should management do?", "Prioritized action matrix"],
    ])

    doc.add_heading("3. Core KPI Framework Matrix", level=1)
    _add_report_table(doc, ["Metric", "Value", "Calculation Method", "Business Impact"], [
        ["Total Titles", f"{kpis['total_shows']:,}", "Count of catalog rows", "Portfolio scale"],
        ["Movies", f"{kpis['movie_count']:,} ({kpis['movies_share']:.1f}%)", "Movie rows / total rows", "Film-led portfolio balance"],
        ["TV Shows", f"{kpis['tv_show_count']:,} ({kpis['tv_share']:.1f}%)", "TV rows / total rows", "Episodic retention base"],
        ["Global Reach", str(kpis["geographic_reach"]), "Distinct countries in country field", "Localization footprint"],
        ["Content Diversity", str(kpis["genre_diversity"]), "Distinct listed genres", "Choice breadth"],
    ])

    doc.add_heading("4. Dataset Architecture & Data Quality Audit", level=1)
    doc.add_paragraph("The application downloads shivamb/netflix-shows through kagglehub, identifies the CSV artifact, validates source fields, normalizes dates and numeric duration values, and derives audience and season fields without changing the source rating semantics.")
    _add_report_table(doc, ["Field / Check", "Observed Result", "Interpretation"], [
        ["Rows", validation_report.get("rows", 0), "Source snapshot size"],
        ["Columns", validation_report.get("columns", 0), "Multi-attribute catalog schema"],
        ["Missing directors", f"{validation_report.get('missing', {}).get('director', 0)}%", "Metadata completeness limitation"],
        ["Missing countries", f"{validation_report.get('missing', {}).get('country', 0)}%", "Geographic attribution limitation"],
        ["Rating definition", "Categorical maturity label", "Not an IMDb score or quality metric"],
        ["Duplicate rows", validation_report.get("duplicates", 0), "Validation control"],
    ])

    doc.add_heading("5. Analytical Deep-Dive & Findings", level=1)
    doc.add_paragraph("Content velocity is measured from date_added using yearly acquisition counts and a monthly seasonality curve. Runtime analysis uses minute values for movies only. TV retention structure is measured from season counts for TV rows only, avoiding the common schema error of treating movie runtimes as TV seasons.")
    doc.add_paragraph(f"The current TV portfolio contains {len(tv_df):,} shows, of which {single_season_share:.1f}% are single-season. Audience maturity segmentation groups ratings into Adults (18+), Teens (13-17), Kids & Family (<13), and Not Rated. These buckets support portfolio breadth decisions without inventing a numeric quality score.")

    doc.add_heading("6. Visual Evidence Placeholders", level=1)
    for placeholder in [
        "[INSERT DASHBOARD SCREENSHOT 1: LEVEL 1 EXECUTIVE OVERVIEW & KPI METRICS]",
        "[INSERT DASHBOARD SCREENSHOT 2: LEVEL 2 TRENDS & CONTENT VELOCITY CHARTS]",
        "[INSERT DASHBOARD SCREENSHOT 3: LEVEL 3 CONTENT DRIVERS & SEASON RETENTION]",
        "[INSERT DASHBOARD SCREENSHOT 4: LEVEL 4 & 5 RISKS, OPPORTUNITIES & STRATEGIC ACTIONS]",
    ]:
        _add_visual_placeholder(doc, placeholder)

    doc.add_heading("7. Strategic Recommendations & Prioritized Action Matrix", level=1)
    _add_report_table(doc, ["Initiative", "Target Problem", "Expected Business Impact", "Implementation Timeline"], [
        ["US/Canada licensing retention", "Mature-market saturation and catalog aging", "Protect engagement and reduce avoidable churn", "0-6 months"],
        ["India and South Korea local acquisition", "APAC localization whitespace", "Increase regional relevance and subscriber acquisition", "6-12 months"],
        ["EMEA and LATAM expansion", "Uneven international catalog depth", "Broaden language and cultural coverage", "6-18 months"],
        ["Multi-season renewals", "Single-season TV churn exposure", "Improve episodic retention and franchise value", "0-12 months"],
    ])
    for item in recommendations:
        doc.add_paragraph(f"{item['Priority']}. {item['Theme']}: {item['Recommendation']}")

    doc.add_heading("8. Technical Learning Outcomes & References", level=1)
    doc.add_paragraph("This project developed skills in schema validation, pandas transformation, Streamlit caching and layout, Plotly visual analytics, categorical segmentation, business recommendation design, and automated Word report generation. The implementation remains intentionally consolidated in app.py to meet the single-file capstone constraint.")
    doc.add_paragraph("References:")
    doc.add_paragraph("Kaggle Netflix Titles dataset: https://www.kaggle.com/datasets/shivamb/netflix-shows")
    doc.add_paragraph("IBM SkillsBuild Data Analytics with AI curriculum and internship materials.")
    doc.add_paragraph("Streamlit, pandas, Plotly, kagglehub, and python-docx documentation.")
    return doc


def main():
    st.set_page_config(page_title="Netflix Content Analytics", layout="wide")
    st.title("🎬 Netflix Content Strategy & Catalog Analytics Platform")
    st.caption("Business intelligence view of Netflix catalog strategy across content mix, audience maturity, risks, and market expansion opportunities.")

    df, validation_report = load_and_prepare_data()
    if df.empty:
        st.warning("Dataset is unavailable. Please verify Kaggle access and try again.")
        return

    with st.sidebar:
        st.header("Filters")
        date_values = pd.to_datetime(df["date_added"].dropna())
        date_min = date_values.min() if not date_values.empty else pd.Timestamp.today()
        date_max = date_values.max() if not date_values.empty else pd.Timestamp.today()
        start_date, end_date = st.date_input("Date range", [date_min.date(), date_max.date()])

        type_options = ["Movie", "TV Show"]
        selected_types = st.multiselect("Content type", type_options, default=type_options)

        genre_options = sorted(set(flatten_list_values(df["listed_in"])))
        selected_genres = st.multiselect("Genres", genre_options, default=[])

        country_options = sorted(set(flatten_list_values(df["country"])))
        selected_country = st.selectbox("Country", ["All"] + country_options, index=0)

        maturity_options = ["Adults (18+)", "Teens (13-17)", "Kids & Family (<13)", "Not Rated"]
        selected_maturity = st.multiselect("Audience segment", maturity_options, default=maturity_options)

    filtered_df = df.copy()
    if start_date and end_date:
        filtered_df = filtered_df[(filtered_df["date_added"].notna()) & (filtered_df["date_added"].between(pd.Timestamp(start_date), pd.Timestamp(end_date)))]
    if selected_types:
        filtered_df = filtered_df[filtered_df["type"].isin(selected_types)]
    if selected_genres:
        filtered_df = filtered_df[filtered_df["listed_in"].apply(lambda x: any(g.strip() in str(x) for g in selected_genres))]
    if selected_country != "All":
        filtered_df = filtered_df[filtered_df["country"].apply(lambda x: selected_country in [p.strip() for p in str(x).split(",") if p.strip()])]
    if selected_maturity:
        filtered_df = filtered_df[filtered_df["rating_segment"].isin(selected_maturity)]

    kpis = calculate_kpis(filtered_df)
    trends = build_trend_data(filtered_df)
    drivers = build_driver_data(filtered_df)
    risks, opportunities = build_risk_opportunity_data(filtered_df)
    recommendations = generate_recommendations(filtered_df, kpis, trends, drivers, risks, opportunities)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Level 1: KPIs",
        "📈 Level 2: Trends",
        "🔍 Level 3: Drivers",
        "⚠️ Level 4: Risks & Opportunities",
        "✅ Level 5: Actions",
        "📄 Report",
    ])

    with tab1:
        st.subheader("Overview & KPI Summary")
        st.markdown("This dashboard explains what is in the Netflix catalog, how it is growing, and which audience segments drive acquisition and retention risk.")

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Titles", f"{kpis['total_shows']:,}")
        with col2:
            st.metric("Movies", f"{kpis['movie_count']:,}", f"{kpis['movies_share']:.1f}% Catalog Share")
        with col3:
            st.metric("TV Shows", f"{kpis['tv_show_count']:,}", f"{kpis['tv_share']:.1f}% Catalog Share")
        with col4:
            st.metric("Global Reach", f"{kpis['geographic_reach']} Countries")
        with col5:
            st.metric("Content Diversity", f"{kpis['genre_diversity']} Unique Genres")

        if not filtered_df.empty:
            st.plotly_chart(build_maturity_chart(filtered_df), use_container_width=True)

        st.write("### Data Quality Summary")
        missing_summary = ", ".join(f"{col}: {val}%" for col, val in validation_report.get("missing", {}).items()) or "No major missing values detected."
        st.info(f"Rows: {validation_report.get('rows', 0)} | Columns: {validation_report.get('columns', 0)} | Duplicates: {validation_report.get('duplicates', 0)} | Missing: {missing_summary}")

    with tab2:
        st.subheader("Level 2: Trends")
        if not trends["yearly_additions"].empty:
            st.plotly_chart(build_acquisition_trend(filtered_df), use_container_width=True)
        if not trends["monthly_additions"].empty:
            st.plotly_chart(px.line(trends["monthly_additions"], x="Month", y="Titles Added", markers=True, title="Monthly additions"), use_container_width=True)

    with tab3:
        st.subheader("Level 3: Content Drivers")
        if not drivers["top_genres"].empty:
            st.plotly_chart(build_top_genres_chart(filtered_df), use_container_width=True)

        if not filtered_df.empty:
            movie_runtime = filtered_df[(filtered_df["type"] == "Movie") & filtered_df["duration_minutes"].notna()]
            if not movie_runtime.empty:
                fig = px.histogram(movie_runtime, x="duration_minutes", nbins=20, title="Movie runtime distribution")
                fig.update_layout(template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

            tv_df = filtered_df[filtered_df["type"] == "TV Show"].copy()
            if not tv_df.empty:
                tv_df["season_bucket"] = tv_df["season_count"].apply(lambda x: "1 Season" if pd.notna(x) and x <= 1 else "Multi-Season")
                season_counts = tv_df["season_bucket"].value_counts().reset_index()
                season_counts.columns = ["Season Structure", "Count"]
                fig = px.pie(season_counts, names="Season Structure", values="Count", title="TV show season retention")
                st.plotly_chart(fig, use_container_width=True)

        if not drivers["maturity_distribution"].empty:
            st.plotly_chart(px.bar(drivers["maturity_distribution"], x="Audience Segment", y="Count", color="Audience Segment", title="Audience maturity mix"), use_container_width=True)

    with tab4:
        st.subheader("Level 4: Risks & Opportunities")
        risk_df = pd.DataFrame(risks)
        opp_df = pd.DataFrame(opportunities)

        if not risk_df.empty:
            st.markdown("### Risk Matrix")
            st.dataframe(risk_df, use_container_width=True)
        else:
            st.info("No major catalog risks were detected in the current view.")

        if not opp_df.empty:
            st.markdown("### Opportunity Matrix")
            st.dataframe(opp_df, use_container_width=True)
        else:
            st.info("No material white-space opportunities were detected in the current view.")

    with tab5:
        st.subheader("Level 5: Strategic Actions")
        for idx, rec in enumerate(recommendations, start=1):
            st.markdown(f"### {idx}. {rec['Theme']}")
            st.write(rec["Recommendation"])
            st.caption(f"Impact: {rec['Impact']}")

    with tab6:
        st.subheader("Generate Project Report")

        kpi_summary = pd.DataFrame(
            [
                ["Total Shows", kpis["total_shows"]],
                ["Movies", f"{kpis['movie_count']} ({kpis['movies_share']:.1f}%)"],
                ["TV Shows", f"{kpis['tv_show_count']} ({kpis['tv_share']:.1f}%)"],
                ["Countries", kpis["geographic_reach"]],
                ["Genres", kpis["genre_diversity"]],
            ],
            columns=["Metric", "Value"],
        )
        st.dataframe(kpi_summary, use_container_width=True)

        report_doc = generate_project_report(kpis, validation_report, recommendations, filtered_df)
        report_buffer = io.BytesIO()
        report_doc.save(report_buffer)
        report_buffer.seek(0)

        st.download_button(
            label="Download Project Report",
            data=report_buffer.getvalue(),
            file_name="Himanshu_Pathak_Netflix_Project_Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


if __name__ == "__main__":
    main()
