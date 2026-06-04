# Business Churn EDA Workflow

## Purpose

This workflow turns the cleaned customer, activity, and support interaction
tables into business-oriented churn intelligence. It is designed for analytics
storytelling, stakeholder review, and downstream feature planning.

No machine learning models are trained in this stage.

## Inputs

- `data/processed/customers_cleaned.csv`
- `data/processed/customer_activity_cleaned.csv`
- `data/processed/support_interactions_cleaned.csv`

## Outputs

- `reports/exports/customer_churn_analytical_dataframe.csv`
- `reports/business_reports/business_kpi_scorecard.csv`
- `reports/business_reports/high_risk_customers.csv`
- `reports/business_reports/low_engagement_customers.csv`
- `reports/business_reports/high_value_customers.csv`
- `reports/business_reports/churn_by_contract.csv`
- `reports/business_reports/churn_by_tenure_segment.csv`
- `reports/business_reports/churn_by_activity_status.csv`
- `reports/business_reports/churn_by_support_burden.csv`
- `reports/business_reports/churn_by_revenue_segment.csv`
- `reports/business_reports/business_churn_eda_report.md`
- `reports/figures/*.png`

## Analytical Grain

The unified analytical dataframe is one row per `unified_customer_id`.

The workflow aggregates:

- Activity records into recency, frequency, monetary, return, and product breadth metrics
- Support tickets into burden, dissatisfaction, priority, resolution, and channel metrics
- Customer records into churn, contract, tenure, revenue, and service-plan segments

## Business KPIs

The KPI scorecard includes:

- Churn rate
- Retention rate
- Average revenue per user using monthly charges
- Average total charges
- Estimated CLV indicator
- Monthly revenue at risk
- Activity coverage and invoice frequency
- Support coverage, ticket burden, open ticket rate, and satisfaction

## Segmentation Logic

Customers are segmented by:

- Tenure maturity
- Activity recency
- Support burden
- Monthly revenue quartile
- Estimated CLV quartile
- Rule-based churn risk score

The risk score is not a model. It is a transparent business heuristic combining
known churn signals such as month-to-month contracts, early tenure, missing
activity, support friction, electronic checks, and high monthly charges.

## Run Command

From the project root:

```bash
python src/analysis/business_churn_eda.py
```
