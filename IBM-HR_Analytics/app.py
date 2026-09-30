"""IBM HR Analytics: Attrition, Income and Workforce Segmentation.

Single-file Streamlit capstone. Data preparation, analysis, models, charts,
UI and in-app PDF report generation intentionally live in this module.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import kagglehub
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    precision_recall_curve,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

st.set_page_config(
    page_title="People Signals: IBM HR Analytics",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;600;700;800&display=swap');
    :root { --ink:#18211f; --muted:#66736d; --paper:#f5f5ef; --teal:#0b6e69; --coral:#d96c4f; --line:#d9ded7; }
    .stApp { background:var(--paper); color:var(--ink); font-family:'Manrope', sans-serif; }
    h1,h2,h3 { letter-spacing:0 !important; color:var(--ink); }
    h1 { font-weight:800; font-size:2.35rem; }
    [data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:8px; padding:1rem; }
    [data-testid="stMetricLabel"] { color:var(--muted); font-size:.77rem; text-transform:uppercase; letter-spacing:.05em; }
    [data-testid="stMetricValue"] { color:var(--teal); font-weight:800; }
    .insight { background:#e3efeb; border-left:4px solid var(--teal); padding:.8rem 1rem; margin:.75rem 0 1.1rem; border-radius:0 6px 6px 0; }
    .eyebrow { color:var(--coral); font-family:'DM Mono', monospace; font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }
    .mono { font-family:'DM Mono', monospace; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- DATA LOADING -----------------------------
@st.cache_data(show_spinner="Downloading and preparing the IBM HR dataset...")
def load_data() -> pd.DataFrame:
    path = kagglehub.dataset_download("pavansubhasht/ibm-hr-analytics-attrition-dataset")
    csv_path = Path(path) / "WA_Fn-UseC_-HR-Employee-Attrition.csv"
    data = pd.read_csv(csv_path)
    # Drop constants and an identifier at load time: they have no predictive signal.
    data = data.drop(columns=["EmployeeCount", "StandardHours", "Over18", "EmployeeNumber"])
    data["AttritionFlag"] = (data["Attrition"] == "Yes").astype(int)
    tenure_order = ["0-1", "2-3", "4-5", "6-10", "11+"]
    data["TenureBucket"] = pd.Categorical(pd.cut(
        data["YearsAtCompany"],
        bins=[-1, 1, 3, 5, 10, np.inf],
        labels=tenure_order,
    ), categories=tenure_order, ordered=True)
    data["DistanceBucket"] = pd.cut(
        data["DistanceFromHome"], bins=[-1, 5, 15, np.inf], labels=["Near (0-5)", "Medium (6-15)", "Far (16+)"],
    ).astype(str)
    return data


# ----------------------------- MODEL PREPARATION -----------------------------
CLASSIFICATION_LEAKAGE = ["Attrition", "AttritionFlag"]
REGRESSION_LEAKAGE = ["MonthlyIncome", "Attrition", "AttritionFlag"]

def feature_frame(data: pd.DataFrame, target: str) -> tuple[pd.DataFrame, pd.Series]:
    excluded = CLASSIFICATION_LEAKAGE if target == "AttritionFlag" else REGRESSION_LEAKAGE
    x_data = data.drop(columns=[c for c in excluded if c in data.columns]).copy()
    y_data = data[target]
    return x_data, y_data


def build_preprocessor(x_data: pd.DataFrame) -> ColumnTransformer:
    categorical = x_data.select_dtypes(include=["object", "category"]).columns.tolist()
    numerical = [column for column in x_data.columns if column not in categorical]
    return ColumnTransformer(
        [("numeric", StandardScaler(), numerical), ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical)],
        remainder="drop",
    )


@st.cache_resource(show_spinner="Training attrition models...")
def train_attrition_models(data: pd.DataFrame) -> dict[str, Any]:
    x_data, y_data = feature_frame(data, "AttritionFlag")
    x_train, x_test, y_train, y_test = train_test_split(
        x_data, y_data, test_size=.25, random_state=42, stratify=y_data
    )
    baseline = Pipeline([("prep", build_preprocessor(x_data)), ("model", LogisticRegression(max_iter=2000, class_weight="balanced"))])
    baseline.fit(x_train, y_train)
    tuned = Pipeline([("prep", build_preprocessor(x_data)), ("model", RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1))])
    search = GridSearchCV(
        tuned,
        {"model__n_estimators": [150], "model__max_depth": [None, 8], "model__min_samples_leaf": [1, 3]},
        cv=StratifiedKFold(n_splits=4, shuffle=True, random_state=42), scoring="roc_auc", n_jobs=-1,
    )
    search.fit(x_train, y_train)
    probabilities = search.predict_proba(x_test)[:, 1]
    default_predictions = (probabilities >= 0.5).astype(int)
    precision, recall, thresholds = precision_recall_curve(y_test, probabilities)
    f1_values = (2 * precision[:-1] * recall[:-1]) / (precision[:-1] + recall[:-1] + 1e-12)
    eligible = np.where(recall[:-1] >= 0.5)[0]
    best_index = eligible[np.argmax(f1_values[eligible])] if len(eligible) else int(np.argmax(f1_values))
    optimal_threshold = float(thresholds[best_index])
    predictions = (probabilities >= optimal_threshold).astype(int)
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    metrics = {
        "f1": f1_score(y_test, predictions), "default_f1": f1_score(y_test, default_predictions),
        "optimal_threshold": optimal_threshold, "confusion_matrix": matrix.tolist(),
        "roc_auc": roc_auc_score(y_test, probabilities),
        "precision": precision_score(y_test, predictions), "recall": recall_score(y_test, predictions),
    }
    return {"baseline": baseline, "model": search.best_estimator_, "metrics": metrics, "x_test": x_test, "y_test": y_test, "features": x_data.columns.tolist()}


@st.cache_resource(show_spinner="Training income models...")
def train_income_models(data: pd.DataFrame) -> dict[str, Any]:
    x_data, y_data = feature_frame(data, "MonthlyIncome")
    x_train, x_test, y_train, y_test = train_test_split(x_data, y_data, test_size=.25, random_state=42)
    baseline = Pipeline([("prep", build_preprocessor(x_data)), ("model", LinearRegression())])
    baseline.fit(x_train, y_train)
    tuned = Pipeline([("prep", build_preprocessor(x_data)), ("model", RandomForestRegressor(random_state=42, n_jobs=-1))])
    search = GridSearchCV(
        tuned, {"model__n_estimators": [150], "model__max_depth": [None, 10], "model__min_samples_leaf": [1, 3]},
        cv=4, scoring="neg_root_mean_squared_error", n_jobs=-1,
    )
    search.fit(x_train, y_train)
    predictions = search.predict(x_test)
    metrics = {"rmse": mean_squared_error(y_test, predictions) ** .5, "mae": mean_absolute_error(y_test, predictions), "r2": r2_score(y_test, predictions)}
    return {"baseline": baseline, "model": search.best_estimator_, "metrics": metrics, "features": x_data.columns.tolist()}


@st.cache_resource(show_spinner="Finding employee segments...")
def build_clusters(data: pd.DataFrame) -> tuple[pd.DataFrame, KMeans]:
    cluster_columns = ["YearsAtCompany", "JobSatisfaction", "WorkLifeBalance", "EnvironmentSatisfaction", "MonthlyIncome"]
    values = StandardScaler().fit_transform(data[cluster_columns])
    model = KMeans(n_clusters=4, n_init=20, random_state=42)
    clustered = data.copy()
    clustered["Segment"] = model.fit_predict(values)
    summary = clustered.groupby("Segment", as_index=False).agg(
        Employees=("Segment", "size"), AttritionRate=("AttritionFlag", "mean"),
        AvgIncome=("MonthlyIncome", "mean"), AvgTenure=("YearsAtCompany", "mean"),
        AvgSatisfaction=("JobSatisfaction", "mean"),
    )
    clustered = clustered.merge(summary, on="Segment", suffixes=("", "Summary"))
    return clustered, model


# ----------------------------- PRESENTATION HELPERS -----------------------------
def insight_box(items: list[str]) -> None:
    st.markdown("<div class='insight'><b>Key insights</b><br>" + "<br>".join(f"• {item}" for item in items) + "</div>", unsafe_allow_html=True)


def section_heading(level: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='eyebrow'>{level}</div><h1>{title}</h1><p>{subtitle}</p>", unsafe_allow_html=True)


def plot_layout(figure: go.Figure, height: int = 370) -> go.Figure:
    for trace in figure.data:
        if not trace.name:
            trace.name = "Feature importance" if figure.layout.yaxis.title.text == "Feature" else str(figure.layout.title.text or "Series").replace("<br>", " ")
        elif trace.name in {"No", "Yes"}:
            trace.name = f"Attrition = {trace.name}"
        trace.showlegend = True
    figure.update_traces(textfont=dict(color="#1a1a1a"))
    figure.update_layout(
        height=height, margin=dict(l=155, r=20, t=52, b=55),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope", color="#1a1a1a"), font_color="#1a1a1a",
        legend_title_text="", legend=dict(font=dict(color="#1a1a1a")),
        xaxis=dict(tickfont=dict(color="#1a1a1a"), title_font=dict(color="#1a1a1a")),
        yaxis=dict(tickfont=dict(color="#1a1a1a"), title_font=dict(color="#1a1a1a")),
    )
    return figure


def feature_importance(model: Pipeline, x_data: pd.DataFrame, y_data: pd.Series) -> pd.DataFrame:
    result = permutation_importance(model, x_data, y_data, n_repeats=5, random_state=42, scoring="roc_auc", n_jobs=-1)
    return pd.DataFrame({"Feature": x_data.columns, "Importance": result.importances_mean}).sort_values("Importance", ascending=False).head(12)


# ----------------------------- REPORT GENERATION -----------------------------
def build_pdf(data: pd.DataFrame, attrition: dict[str, Any], income: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=.6 * inch, leftMargin=.6 * inch, topMargin=.55 * inch, bottomMargin=.55 * inch)
    styles = getSampleStyleSheet()
    story = [Paragraph("People Signals: IBM HR Analytics", styles["Title"]), Paragraph("Dashboard state report", styles["Heading2"]), Spacer(1, 12)]
    kpis = [
        ["Total employees", f"{len(data):,}"], ["Attrition rate", f"{data['AttritionFlag'].mean():.1%}"],
        ["Average monthly income", f"${data['MonthlyIncome'].mean():,.0f}"], ["Departments", f"{data['Department'].nunique()}"],
        ["Attrition F1", f"{attrition['metrics']['f1']:.3f}"], ["Attrition ROC-AUC", f"{attrition['metrics']['roc_auc']:.3f}"],
        ["Income RMSE", f"${income['metrics']['rmse']:,.0f}"], ["Income R2", f"{income['metrics']['r2']:.3f}"],
    ]
    table = Table(kpis, colWidths=[2.2 * inch, 1.25 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e3efeb")), ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#b8c8c0")), ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("PADDING", (0, 0), (-1, -1), 7)]))
    story.extend([table, Spacer(1, 14), Paragraph("Interpretation", styles["Heading2"]), Paragraph("Use the interactive dashboard to inspect tenure direction, attrition drivers, model risk scores and employee segments. This export captures the current calculated KPI and model state without fabricating additional values.", styles["BodyText"]), Spacer(1, 10)])
    story.append(Paragraph("Model notes", styles["Heading2"]))
    story.append(Paragraph("Attrition uses class-balanced logistic regression as a baseline and a cross-validated, tuned random forest as the primary model. Monthly income uses linear regression as a baseline and a tuned random forest regressor. Constants and identifiers are excluded at load time; target columns are excluded from their own feature frames.", styles["BodyText"]))
    document.build(story)
    return buffer.getvalue()


# ----------------------------- APP -----------------------------
data = load_data()
attrition_models = train_attrition_models(data)
income_models = train_income_models(data)
clustered_data, _ = build_clusters(data)

with st.sidebar:
    st.markdown("<div class='eyebrow'>IBM HR / 2026</div>", unsafe_allow_html=True)
    st.title("People Signals: IBM HR Analytics")
    st.caption("A decision surface for retention, mobility and workforce planning.")
    page = st.radio("Explore", ["Level 1 · KPIs", "Level 2 · Trends", "Level 3 · Drivers", "Level 4 · Risks & Opportunities", "Level 5 · Strategic Actions", "Generate Report"], label_visibility="collapsed")
    st.divider()
    st.caption(f"{len(data):,} employee records • Kaggle source")

if page == "Level 1 · KPIs":
    section_heading("LEVEL 1 / WHAT IS HAPPENING?", "The workforce at a glance", "A baseline view of scale, attrition and earning power.")
    cols = st.columns(4)
    cols[0].metric("Total Employees", f"{len(data):,}")
    cols[1].metric("Overall Attrition Rate", f"{data['AttritionFlag'].mean():.1%}")
    cols[2].metric("Average Monthly Income", f"${data['MonthlyIncome'].mean():,.0f}")
    cols[3].metric("Active Departments / Segments", f"{data['Department'].nunique()} / {data['JobRole'].nunique()}")
    st.subheader("Attrition mix")
    mix = data["Attrition"].value_counts().rename_axis("Status").reset_index(name="Employees")
    st.plotly_chart(plot_layout(px.bar(mix, x="Status", y="Employees", color="Status", text="Employees", labels={"Status": "Attrition", "Employees": "Employees"}, color_discrete_map={"No": "#0b6e69", "Yes": "#d96c4f"})), use_container_width=True)
    insight_box([f"{data['AttritionFlag'].mean():.1%} of employees are marked for attrition.", f"The typical employee earns ${data['MonthlyIncome'].mean():,.0f} per month.", f"The data spans {data['Department'].nunique()} departments and {data['JobRole'].nunique()} job roles."])

elif page == "Level 2 · Trends":
    section_heading("LEVEL 2 / DIRECTION KYA HAI?", "Tenure is the time axis", "This dataset has no calendar dates, so tenure and role tenure show direction over an employee lifecycle.")
    left, right = st.columns(2)
    with left:
        tenure = data.groupby("TenureBucket", observed=False).agg(AttritionRate=("AttritionFlag", "mean"), Employees=("AttritionFlag", "size")).reset_index()
        st.plotly_chart(plot_layout(px.line(tenure, x="TenureBucket", y="AttritionRate", markers=True, title="Attrition rate by tenure bucket", category_orders={"TenureBucket": ["0-1", "2-3", "4-5", "6-10", "11+"]}, labels={"AttritionRate": "Attrition rate"})), use_container_width=True)
    with right:
        income_curve = data.groupby(["JobLevel", "YearsAtCompany"], as_index=False)["MonthlyIncome"].mean()
        st.plotly_chart(plot_layout(px.line(income_curve, x="YearsAtCompany", y="MonthlyIncome", color="JobLevel", title="Income growth by job level", labels={"MonthlyIncome": "Average monthly income"})), use_container_width=True)
    peak_bucket = tenure.loc[tenure["AttritionRate"].idxmax(), "TenureBucket"]
    insight_box([f"The highest observed attrition bucket is {peak_bucket} at {tenure['AttritionRate'].max():.1%}.", "Tenure is used as a lifecycle proxy because the source contains no event dates.", "Income curves let HR compare progression patterns across job levels."])

elif page == "Level 3 · Drivers":
    section_heading("LEVEL 3 / WHY IS IT HAPPENING?", "The pressure points", "Compare attrition across work design, role context and employee experience.")
    selected = st.selectbox("Breakdown", ["OverTime", "JobRole", "Department", "MaritalStatus", "DistanceBucket"])
    driver = data.groupby(selected, as_index=False).agg(AttritionRate=("AttritionFlag", "mean"), Employees=("AttritionFlag", "size"))
    left, right = st.columns([1.2, 1])
    with left:
        st.plotly_chart(plot_layout(px.bar(driver.sort_values("AttritionRate"), x="AttritionRate", y=selected, orientation="h", color="AttritionRate", color_continuous_scale=["#b8d8d2", "#d96c4f"], title=f"Attrition by {selected}", labels={"AttritionRate": "Attrition rate"})), use_container_width=True)
    with right:
        satisfaction = st.selectbox("Experience measure", ["JobSatisfaction", "WorkLifeBalance", "EnvironmentSatisfaction"])
        distribution = data.groupby([satisfaction, "Attrition"], as_index=False).size()
        st.plotly_chart(plot_layout(px.bar(distribution, x=satisfaction, y="size", color="Attrition", barmode="group", title=f"{satisfaction} distribution", labels={"size": "Employees"})), use_container_width=True)
    top_driver = driver.loc[driver["AttritionRate"].idxmax()]
    insight_box([f"{top_driver[selected]} has the highest {selected} attrition rate at {top_driver['AttritionRate']:.1%}.", f"The selected experience measure is shown split by attrition status.", "Use employee counts alongside rates before prioritising an intervention."])

elif page == "Level 4 · Risks & Opportunities":
    section_heading("LEVEL 4 / RISKS & OPPORTUNITIES", "From patterns to people", "Model-led risk signals and practical employee segments for targeted action.")
    importance = feature_importance(attrition_models["model"], attrition_models["x_test"], attrition_models["y_test"])
    st.subheader("Top attrition risk drivers")
    st.plotly_chart(plot_layout(px.bar(importance.sort_values("Importance", ascending=True), x="Importance", y="Feature", orientation="h", color="Importance", color_continuous_scale=["#b8d8d2", "#0b6e69"], labels={"Importance": "Permutation importance", "Feature": "Feature"})), use_container_width=True)
    x_all, _ = feature_frame(data, "AttritionFlag")
    risk_scores = attrition_models["model"].predict_proba(x_all)[:, 1]
    high_risk = data[["Age", "JobRole", "Department", "OverTime", "YearsAtCompany", "MonthlyIncome", "Attrition"]].copy()
    high_risk["RiskScore"] = risk_scores
    st.subheader("High-risk employee list")
    st.dataframe(
        high_risk.sort_values("RiskScore", ascending=False).head(25), use_container_width=True, hide_index=True,
        column_config={
            "Age": st.column_config.NumberColumn("Age", width="small"), "JobRole": st.column_config.TextColumn("Job role", width="medium"),
            "Department": st.column_config.TextColumn("Department", width="medium"), "OverTime": st.column_config.TextColumn("Overtime", width="small"),
            "YearsAtCompany": st.column_config.NumberColumn("Years at company", format="%d", width="small"),
            "MonthlyIncome": st.column_config.NumberColumn("Monthly income", format="$%d", width="medium"),
            "Attrition": st.column_config.TextColumn("Actual attrition", width="small"), "RiskScore": st.column_config.NumberColumn("Risk score", format="%.1f%%", width="medium"),
        },
    )
    st.caption(f"Optimal classification threshold: {attrition_models['metrics']['optimal_threshold']:.3f}. Employees at or above this score are prioritised for review.")
    matrix = pd.DataFrame(attrition_models["metrics"]["confusion_matrix"], index=["Actual No", "Actual Yes"], columns=["Predicted No", "Predicted Yes"])
    st.dataframe(matrix, use_container_width=False, hide_index=False, column_config={column: st.column_config.NumberColumn(column, format="%d", width="medium") for column in matrix.columns})
    st.subheader("Employee segments")
    summary = clustered_data.groupby("Segment", as_index=False).agg(Employees=("Segment", "size"), AttritionRate=("AttritionFlag", "mean"), AvgIncome=("MonthlyIncome", "mean"), AvgTenure=("YearsAtCompany", "mean"), AvgSatisfaction=("JobSatisfaction", "mean"))
    st.dataframe(
        summary, use_container_width=True, hide_index=True,
        column_config={
            "Segment": st.column_config.NumberColumn("Segment", format="%d", width="small"), "Employees": st.column_config.NumberColumn("Employees", format="%d", width="medium"),
            "AttritionRate": st.column_config.NumberColumn("Attrition rate", format="%.1f%%", width="medium"), "AvgIncome": st.column_config.NumberColumn("Average income", format="$%d", width="medium"),
            "AvgTenure": st.column_config.NumberColumn("Average tenure", format="%.1f", width="medium"), "AvgSatisfaction": st.column_config.NumberColumn("Average satisfaction", format="%.1f", width="large"),
        },
    )
    highest_risk_segment = summary.loc[summary["AttritionRate"].idxmax(), "Segment"]
    insight_box([f"Segment {highest_risk_segment} has the highest cluster-level attrition rate at {summary['AttritionRate'].max():.1%}.", f"The table exposes the top 25 employees by predicted risk score ({risk_scores.max():.1%} maximum).", "Segments combine tenure, three satisfaction measures and income; they are action groups, not causal labels."])

elif page == "Level 5 · Strategic Actions":
    section_heading("LEVEL 5 / WHAT SHOULD HR DO?", "A short action register", "Each action is anchored to a dashboard signal and includes a measurable follow-through.")
    drivers = data.groupby("OverTime")["AttritionFlag"].mean()
    roles = data.groupby("JobRole")["AttritionFlag"].mean().sort_values(ascending=False)
    actions = [
        ("01", "Treat overtime as a retention lever", f"Overtime groups differ in observed attrition ({drivers.max():.1%} at the highest group). Pilot workload caps, manager alerts and recovery time; track monthly attrition and overtime incidence."),
        ("02", "Design role-specific retention plans", f"The highest observed role rate is {roles.index[0]} at {roles.iloc[0]:.1%}. Pair career-path conversations with role-level manager coaching and compare the next cohort against baseline."),
        ("03", "Protect the early-tenure window", "Use the tenure-bucket chart to trigger 30/90/180-day check-ins where the lifecycle rate peaks; monitor attrition by bucket rather than relying on an annual average."),
        ("04", "Make risk review human-in-the-loop", f"Use the top-risk list and segments to prioritise conversations, not automated decisions. Audit outcomes against the model's {attrition_models['metrics']['roc_auc']:.3f} ROC-AUC and refresh the model when workforce mix changes."),
    ]
    for number, title, body in actions:
        st.markdown(f"### <span class='mono'>{number}</span> {title}", unsafe_allow_html=True)
        st.write(body)
        st.divider()
    insight_box(["The most defensible interventions target observable work design and lifecycle signals.", "Model output should prioritise support conversations, never determine employment action.", "Re-measure each intervention against the exact chart metric that motivated it."])

else:
    section_heading("REPORT / CURRENT STATE", "Export a decision brief", "Generate a lightweight PDF from the live dataset and cached model outputs.")
    st.info("The export includes calculated KPIs, model metrics and interpretation notes. The full narrative report with screenshot placeholders lives in docs/Project_Report.docx.")
    st.download_button("Download current dashboard report (PDF)", data=build_pdf(data, attrition_models, income_models), file_name="people_signals_dashboard_report.pdf", mime="application/pdf", type="primary")
    st.subheader("Model quality snapshot")
    a, b = st.columns(2)
    a.metric("Attrition F1 (optimal / default)", f"{attrition_models['metrics']['f1']:.3f} / {attrition_models['metrics']['default_f1']:.3f}")
    b.metric("Income RMSE / R²", f"${income_models['metrics']['rmse']:,.0f} / {income_models['metrics']['r2']:.3f}")
    st.caption(f"Attrition ROC-AUC: {attrition_models['metrics']['roc_auc']:.3f} • Precision: {attrition_models['metrics']['precision']:.3f} • Recall: {attrition_models['metrics']['recall']:.3f} • Optimal threshold: {attrition_models['metrics']['optimal_threshold']:.3f}. Models use a stratified holdout and cross-validation during tuning; classification uses balanced class weights.")
    st.subheader("Attrition confusion matrix at optimal threshold")
    tn, fp, fn, tp = np.asarray(attrition_models["metrics"]["confusion_matrix"]).ravel()
    report_matrix = pd.DataFrame(
        [[f"True Negative = {tn}", f"False Positive = {fp}"], [f"False Negative = {fn}", f"True Positive = {tp}"]],
        index=["Actual No", "Actual Yes"], columns=["Predicted No", "Predicted Yes"],
    )
    st.dataframe(
        report_matrix, use_container_width=False, hide_index=False,
        column_config={
            "Predicted No": st.column_config.TextColumn("Predicted No", width="large"),
            "Predicted Yes": st.column_config.TextColumn("Predicted Yes", width="large"),
        },
    )
    st.caption("Each cell reports the count at the precision-recall-selected threshold, with the classification outcome named explicitly.")
