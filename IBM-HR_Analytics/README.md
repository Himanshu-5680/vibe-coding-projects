# 📊 People Signals: IBM HR Analytics

**A decision surface for retention, mobility and workforce planning — not just another attrition dashboard.**

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red) ![Status](https://img.shields.io/badge/Status-Active-brightgreen)

Every company loses people. Most dashboards just count how many. **People Signals goes one level deeper** — it turns 1,470 employee records from IBM's HR dataset into a live decision tool: who's at risk, why, and what HR should actually *do* about it before it's too late.

---

## 🎯 The problem this solves

HR teams don't lack data — they lack a way to *act* on it. Attrition numbers sit in spreadsheets while the real signals (overtime load, tenure cliffs, role-specific pressure points) stay buried. This dashboard surfaces those signals and converts them into targeted, measurable retention actions.

> ⚠️ Model output here is a **prioritisation aid for human review** — never an automated employment decision.

---

## 🚀 Quick start

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

First run auto-downloads the dataset via `kagglehub`:
[`pavansubhasht/ibm-hr-analytics-attrition-dataset`](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset) — no manual download needed.

---

## 🗺️ Walk through the dashboard

| Level | Question it answers | What's inside |
|---|---|---|
| **1 · KPIs** | What is happening? | Total headcount, attrition rate, avg income, dept/role spread |
| **2 · Trends** | Which direction? | Tenure-bucket attrition curve, income growth by job level |
| **3 · Drivers** | Why is it happening? | Overtime, role, department, marital status, distance × attrition |
| **4 · Risks & Opportunities** | What's next? | Feature-importance risk model, high-risk employee list, KMeans segments |
| **5 · Strategic Actions** | What should HR do? | Numbered actions, each tied back to a specific chart |
| **📄 Generate Report** | Prove it | One-click PDF export of the live dashboard state |

Every level ends with a **Key Insights** callout — no digging through charts to find the takeaway.

---

## 🔬 Under the hood

- **Cleaning:** drops constants (`EmployeeCount`, `StandardHours`, `Over18`) and the `EmployeeNumber` ID — nothing that can't teach the model anything.
- **Attrition model:** balanced Logistic Regression baseline → GridSearchCV-tuned Random Forest, evaluated on F1 / ROC-AUC / Precision / Recall (not vanity accuracy).
- **Income model:** Linear Regression baseline → tuned Random Forest Regressor, evaluated on RMSE / MAE / R².
- **Segmentation:** KMeans on tenure, satisfaction, work-life balance, and income — turns "everyone" into actionable groups.
- **Performance:** `st.cache_data` for cleaning, `st.cache_resource` for models — the dashboard never retrains itself into a coffee break.

No hard-coded numbers anywhere. Every metric you see is computed live from the dataset on that run.

---

## 📦 Requirements

Python 3.10+, pinned versions in `requirements.txt`. Kaggle credentials may be needed for `kagglehub` depending on your environment.

---

## 📁 Also in this repo

`docs/Project_Report.docx` — a written report with a screenshot placeholder for every dashboard level, for anyone who'd rather read than click.

## 🌐 Live Web Application

The analytics platform is fully deployed and accessible in the cloud via Streamlit Community Cloud:

* **Live URL:** [https://ibmhranalytics.streamlit.app](https://ibmhranalytics.streamlit.app)
* **Hosting Platform:** Streamlit Cloud
* **Status:** 🟢 Active & Deployed

> **Evaluator Note:** You can test all 5 Business Intelligence levels (KPIs, Tenure Lifecycle Trends, Attrition Drivers, Risk Segmentation, and Strategic HR Actions) directly on the live platform without setting up local dependencies.
