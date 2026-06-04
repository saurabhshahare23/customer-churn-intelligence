# SQL Analytics Layer

This folder contains stakeholder-ready SQL for the Customer Churn Intelligence
Platform.

## Required Base Object

The queries assume a warehouse table named:

```sql
churn_features_master
```

Create the semantic view first:

- `views/vw_churn_customer_analytics.sql`

The view reconstructs business-friendly dimensions from the ML-ready feature
table, including contract type, payment method, internet service, customer value
segment, tenure segment, engagement segment, support burden segment, and health
segment.

## Business Queries

- `business_queries/01_executive_churn_kpis.sql`
  Overall churn rate, retention rate, ARPU, realized revenue loss, and CLV loss.

- `business_queries/02_customer_segmentation.sql`
  Segment-level churn, value, revenue, and risk ranking.

- `business_queries/03_high_risk_customers_and_revenue_at_risk.sql`
  SQL-only high-risk customer list with outreach ranking and revenue exposure.

- `business_queries/04_customer_lifetime_value_analysis.sql`
  CLV concentration and churn loss by value tier, tenure, and contract.

- `business_queries/05_support_burden_analysis.sql`
  Churn and revenue analysis by support volume, complaints, and satisfaction.

- `business_queries/06_engagement_analysis.sql`
  Inactivity, engagement, frequency, and revenue analysis for reactivation.

## Cohort Analysis

- `cohort_analysis/01_tenure_cohort_churn_analysis.sql`
  Lifecycle churn cohorts by tenure, value, and contract.

- `cohort_analysis/02_value_cohort_retention_curve.sql`
  Cohort-style retention curve by value segment and tenure month.

- `cohort_analysis/03_engagement_cohort_analysis.sql`
  Engagement and recency cohorts for reactivation planning.

## Retention Analysis

- `retention_analysis/01_retention_by_contract_and_value.sql`
  Retained revenue and customer base by contract, value, and payment risk.

- `retention_analysis/02_retention_opportunity_prioritization.sql`
  SQL-only retained customer action queue using analytical risk rules.

- `retention_analysis/03_retention_campaign_scenario_sql.sql`
  Simplified SQL campaign simulator for top-risk retained customers.

## Notes

- Queries use CTEs, window functions, ranking, aggregation, and case statements.
- Revenue-at-risk logic is analytical and should be calibrated before finance
  sign-off.
- SQL syntax is written in a warehouse-friendly style. Minor adaptations may be
  needed for a specific engine, especially functions like `CEIL` and
  `CREATE OR REPLACE VIEW`.
