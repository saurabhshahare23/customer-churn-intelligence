# Business Churn EDA Report

## Executive Summary

This exploratory workflow merges cleaned customer, activity, and support data
into a customer-level analytical dataframe. It focuses on business
understanding: churn behavior, customer segments, revenue exposure, engagement
signals, and support dissatisfaction. No machine learning models are trained.

The observed churn rate is **26.54%**, with a retention rate of
**73.46%**. Average monthly revenue per user is **64.76**, and
monthly revenue already associated with churned customers is **139130.85**.

## Unified Analytical Dataset

The unified dataframe is written to `reports/exports/customer_churn_analytical_dataframe.csv`.
It uses `unified_customer_id` as the customer grain and includes:

- Customer subscription and churn attributes
- Activity recency, frequency, monetary value, returns, and product breadth
- Support ticket volume, open ticket counts, priority mix, satisfaction, and resolution timing
- Business segments for tenure, engagement, revenue, support burden, CLV, and risk

## KPI Scorecard

| kpi | value | business_definition |
| --- | --- | --- |
| total_customers | 7043.0 | Count of cleaned customer records. |
| churned_customers | 1869.0 | Customers with observed churn label. |
| retained_customers | 5174.0 | Customers that have not churned. |
| churn_rate_pct | 26.54 | Observed churned customers / total customers. |
| retention_rate_pct | 73.46 | Observed retained customers / total customers. |
| arpu_monthly_charges | 64.76 | Average monthly charge per customer. |
| avg_total_charges | 2283.3 | Average historical charges per customer. |
| avg_estimated_clv_indicator | 2279.58 | Monthly charges multiplied by tenure. |
| monthly_revenue_at_risk | 139130.85 | Monthly recurring revenue tied to churned customers. |
| active_customer_rate_pct | 95.4 | Customers with mapped activity records. |
| avg_invoice_count | 7.61 | Average distinct invoices per customer. |
| avg_net_activity_revenue | 2699.73 | Average mapped activity revenue per customer. |
| support_customer_rate_pct | 68.79 | Customers with support interactions. |
| avg_tickets_per_customer | 1.2 | Average support tickets per customer. |
| open_ticket_rate_pct | 67.3 | Open tickets / all tickets. |
| avg_satisfaction_rating | 3.0 | Average satisfaction among rated customers. |

## Churn Trends

- `month_to_month` has the highest observed churn rate at 42.71% across 3875 customers.
- `0_6_months` has the highest observed churn rate at 52.94% across 1481 customers.
- `mid_high_revenue` has the highest observed churn rate at 37.44% across 1760 customers.

Business interpretation: churn should be read as a behavioral and commercial
pattern, not only as a target label. Contract structure, tenure maturity, and
revenue intensity are especially useful lenses for retention planning.

## Engagement Patterns

| activity_status | customers | avg_monthly_charges | avg_tenure | avg_invoice_count | avg_ticket_count | avg_risk_score | churn_rate_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| inactive_90_plus_days | 3238 | 64.73914453366275 | 32.53798641136504 | 4.1300185299567636 | 1.1837554045707226 | 51.34342186534898 | 27.08 |
| active_last_30_days | 2034 | 64.32863815142576 | 31.69174041297935 | 14.658308751229105 | 1.2295968534906587 | 37.03294001966568 | 26.99 |
| active_31_90_days | 1447 | 65.4109191430546 | 32.44091223220456 | 7.21147201105736 | 1.2107809260539046 | 36.41326883206634 | 25.57 |
| no_activity | 324 | 64.80617283950617 | 34.657407407407405 | 0.0 | 1.1820987654320987 | 49.93827160493827 | 22.53 |

Customers with weak or stale activity deserve dedicated lifecycle review.
Inactivity is especially important when paired with month-to-month contracts,
high monthly charges, or unresolved support issues.

## Support Dissatisfaction Signals

| support_burden_segment | customers | avg_monthly_charges | avg_tenure | avg_invoice_count | avg_ticket_count | avg_risk_score | churn_rate_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| high_support | 12 | 69.25 | 29.833333333333332 | 5.916666666666667 | 6.083333333333333 | 57.083333333333336 | 33.33 |
| low_support | 3958 | 64.71953006568974 | 32.00783223850429 | 7.528044466902476 | 1.3815058110156644 | 47.16397170288024 | 27.11 |
| no_support | 2198 | 65.56289808917198 | 32.23430391264786 | 7.468152866242038 | 0.0 | 35.05686988171065 | 26.84 |
| moderate_support | 875 | 62.878228571428565 | 34.393142857142855 | 8.389714285714286 | 3.346285714285714 | 52.605714285714285 | 23.09 |

Support burden is treated as an experience signal. High ticket volume, open
tickets, critical priorities, refund or cancellation requests, and low
satisfaction ratings can all indicate friction that may precede churn.

## High-Risk Customers

The high-risk list focuses on currently retained customers with elevated
non-model risk scores. There are **1054** retained customers in
the high-risk segment, including **101** high-CLV customers.

| unified_customer_id | contract | tenure | monthly_charges | activity_status | ticket_count | open_ticket_count | avg_satisfaction_rating | churn_risk_score | risk_segment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CUST0005238 | month_to_month | 2 | 100.2 | inactive_90_plus_days | 2.0 | 1.0 | 5.0 | 100 | high_risk |
| CUST0005750 | month_to_month | 9 | 94.05 | inactive_90_plus_days | 2.0 | 1.0 | 3.0 | 100 | high_risk |
| CUST0003803 | month_to_month | 12 | 89.55 | inactive_90_plus_days | 2.0 | 2.0 | 0.0 | 95 | high_risk |
| CUST0002981 | month_to_month | 1 | 89.35 | inactive_90_plus_days | 2.0 | 1.0 | 2.0 | 95 | high_risk |
| CUST0005368 | month_to_month | 1 | 89.25 | inactive_90_plus_days | 2.0 | 1.0 | 4.0 | 95 | high_risk |
| CUST0003425 | month_to_month | 5 | 89.15 | inactive_90_plus_days | 2.0 | 1.0 | 5.0 | 95 | high_risk |
| CUST0001510 | month_to_month | 9 | 85.5 | inactive_90_plus_days | 4.0 | 4.0 | 0.0 | 95 | high_risk |
| CUST0000905 | month_to_month | 12 | 84.6 | inactive_90_plus_days | 2.0 | 0.0 | 2.0 | 95 | high_risk |
| CUST0003468 | month_to_month | 1 | 84.6 | inactive_90_plus_days | 2.0 | 2.0 | 0.0 | 95 | high_risk |
| CUST0002438 | month_to_month | 2 | 84.05 | inactive_90_plus_days | 3.0 | 1.0 | 3.0 | 95 | high_risk |

## Low-Engagement Customers

| unified_customer_id | contract | tenure | monthly_charges | activity_status | days_since_last_activity | invoice_count | net_activity_revenue | churn_risk_score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CUST0006092 | two_year | 72 | 116.75 | no_activity |  | 0.0 | 0.0 | 40 |
| CUST0006276 | two_year | 71 | 116.25 | no_activity |  | 0.0 | 0.0 | 30 |
| CUST0006826 | two_year | 34 | 116.15 | no_activity |  | 0.0 | 0.0 | 20 |
| CUST0005994 | two_year | 72 | 115.05 | no_activity |  | 0.0 | 0.0 | 20 |
| CUST0006122 | two_year | 72 | 113.4 | no_activity |  | 0.0 | 0.0 | 20 |
| CUST0006041 | one_year | 67 | 112.35 | no_activity |  | 0.0 | 0.0 | 30 |
| CUST0006257 | two_year | 72 | 111.6 | no_activity |  | 0.0 | 0.0 | 40 |
| CUST0006063 | two_year | 59 | 111.1 | no_activity |  | 0.0 | 0.0 | 40 |
| CUST0006244 | two_year | 72 | 110.65 | no_activity |  | 0.0 | 0.0 | 50 |
| CUST0006145 | two_year | 70 | 110.2 | no_activity |  | 0.0 | 0.0 | 30 |

## High-Value Customers

| unified_customer_id | contract | tenure | monthly_charges | total_charges | estimated_clv_indicator | invoice_count | ticket_count | churn_risk_score | risk_segment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CUST0005361 | two_year | 72 | 118.75 | 8672.45 | 8550.0 | 44.0 | 1.0 | 5 | low_risk |
| CUST0006994 | two_year | 72 | 118.2 | 8547.15 | 8510.4 | 1.0 | 3.0 | 50 | medium_risk |
| CUST0002687 | two_year | 72 | 117.6 | 8308.9 | 8467.199999999999 | 10.0 | 2.0 | 40 | medium_risk |
| CUST0006856 | two_year | 72 | 117.5 | 8670.1 | 8460.0 | 1.0 | 0.0 | 20 | low_risk |
| CUST0004904 | two_year | 72 | 117.35 | 8436.25 | 8449.199999999999 | 1.0 | 2.0 | 40 | medium_risk |
| CUST0004721 | two_year | 72 | 117.15 | 8529.5 | 8434.800000000001 | 2.0 | 1.0 | 30 | low_risk |
| CUST0006346 | two_year | 71 | 118.65 | 8477.6 | 8424.15 | 2.0 | 1.0 | 25 | low_risk |
| CUST0006893 | two_year | 72 | 116.95 | 8594.4 | 8420.4 | 1.0 | 2.0 | 40 | medium_risk |
| CUST0001030 | two_year | 72 | 116.85 | 8477.7 | 8413.199999999999 | 6.0 | 5.0 | 25 | low_risk |
| CUST0000012 | two_year | 72 | 116.8 | 8456.75 | 8409.6 | 3.0 | 1.0 | 15 | low_risk |

## Key Business Insights

1. Contract and tenure are central churn lenses. Customers on flexible contracts
   and early-tenure customers should be prioritized for onboarding, plan-fit
   reviews, and retention offers.
2. Revenue exposure is not evenly distributed. High monthly charges and high
   estimated CLV should be paired with risk indicators to prioritize
   intervention value.
3. Inactivity is a practical leading indicator. Customers with stale or missing
   activity can be routed into re-engagement campaigns before churn is observed.
4. Support friction adds operational context to churn. Open, critical, refund,
   cancellation, and low-satisfaction tickets should feed customer health
   monitoring.
5. The synthetic identity bridge enables cross-source analysis, but match
   confidence should be considered when making customer-level decisions.

## Visualizations

The workflow saves matplotlib/seaborn charts to `reports/figures/`:

- `churn_rate_by_contract.png`
- `churn_rate_by_tenure_segment.png`
- `churn_rate_by_activity_status.png`
- `churn_rate_by_support_burden.png`
- `churn_rate_by_revenue_segment.png`
- `monthly_charges_by_churn.png`
- `tenure_distribution_by_churn.png`
- `churn_driver_correlation_heatmap.png`
- `value_tenure_support_scatter.png`
