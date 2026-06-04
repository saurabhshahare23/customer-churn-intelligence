# Customer Churn Intelligence Platform

A simple end-to-end churn analytics project that predicts customer churn, recommends retention actions, and estimates revenue impact.

## 🚀 Project Overview

- Built a customer churn workflow from raw data to business insights.
- Cleaned and connected customer, activity, and support datasets.
- Trained churn prediction models and saved model outputs.
- Created retention recommendations and revenue impact summaries.
- Added SQL queries and a Streamlit app for stakeholder reporting.

## 📊 Key Features

- **Churn Prediction**
  - Predicts whether a customer is likely to churn.

- **Customer Risk Scoring**
  - Groups customers into low, medium, and high-risk segments.

- **Retention Recommendations**
  - Suggests actions like discounts, support follow-up, onboarding help, and engagement campaigns.

- **Revenue at Risk Analysis**
  - Estimates how much monthly revenue is exposed to churn.

- **Business Impact Simulation**
  - Compares retention campaign scenarios for high-risk customers.

- **SQL Analytics Layer**
  - Includes business queries for churn rate, retention, cohorts, segments, and revenue analysis.

- **Streamlit Dashboard**
  - Lets users select a customer and view churn probability, risk level, revenue at risk, and recommended action.

## 🛠 Tech Stack

- Python
- SQL
- Pandas
- Scikit-learn
- Joblib
- Streamlit
- Matplotlib
- Plotly

## 📂 Project Structure

```text
customer-churn-intelligence/
├── data/
│   ├── raw/
│   └── processed/
├── models/
│   ├── trained_models/
│   ├── model_metrics/
│   └── feature_importance/
├── notebooks/
├── reports/
│   ├── business_reports/
│   └── figures/
├── sql/
│   ├── business_queries/
│   ├── cohort_analysis/
│   └── retention_analysis/
├── src/
├── deployment/
│   └── streamlit/
├── run_app.ps1
└── README.md
```

## ▶️ Run the App

Open PowerShell from the project folder:

```powershell
cd "E:\6. Projects\customer-churn-intelligence"
```

Run with one command:

```powershell
.\run_app.ps1
```

Or run manually:

```powershell
python -m streamlit run deployment/streamlit/app.py
```

Then open:

```text
http://localhost:8501
```

## 📈 Sample Metrics

| Metric | Value |
|---|---:|
| Total Customers | 7,043 |
| High-Risk Customers | 595 |
| Monthly Revenue at Risk | 110,603.66 |
| Estimated Monthly Recovery | 19,662.01 |

## 🎯 Business Goal

Customer churn directly affects revenue and customer lifetime value.

This project helps identify customers who may leave, understand the main risk signals, and recommend practical retention actions.

It also estimates revenue at risk so business teams can focus on the customers and campaigns that matter most.


##📊 Dashboard

<img width="1914" height="933" alt="image" src="https://github.com/user-attachments/assets/b7e81592-9002-45a8-b9d4-ff4b675d0671" />

<img width="1919" height="898" alt="image" src="https://github.com/user-attachments/assets/0d6f092a-0449-4dda-aafd-52a735876bf7" />

<img width="1919" height="905" alt="image" src="https://github.com/user-attachments/assets/1b1414b1-6d9a-40cd-9948-48d57ddc773f" />


## 🔮 Future Improvements

- SHAP customer explanations
- Real-time scoring
- API deployment
- Better UI
- Automated retraining
- Data quality monitoring

## 👨‍💻 Author

Saurabh Shahare

Email: sourabhshahare19241@gmail.com

LinkedIn: linkedin.com/in/saurabh-shahare

Data Analyst | Customer Analytics | Business Intelligence
