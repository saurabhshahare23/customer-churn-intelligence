# Retention Recommendation Engine Report

## Scope

This workflow converts churn predictions and customer behavior features into
actionable retention recommendations. It does not build dashboards.

## Inputs

- `data/processed/churn_features_master.csv`
- `data/processed/churn_features_master_pre_encoding.csv`
- `models/model_metrics/best_model_test_predictions.csv`
- `models/trained_models/best_churn_model.joblib`

## Recommendation Method

The engine scores all customers with the saved best churn model, assigns risk
segments from churn probability, and applies transparent business rules using:

- Inactivity and engagement score
- Complaint frequency and support burden
- Payment behavior and contract flexibility
- Customer value segment and monthly revenue
- Tenure and customer health

## Risk Segments

- Low risk: churn probability below `0.40`
- Medium risk: churn probability from `0.40` to below `0.70`
- High risk: churn probability `0.70` or higher

## Priority Logic

- `P0 critical`: high-risk, high-value active customers
- `P1 high`: high-risk customers or medium-risk valuable customers
- `P2 medium`: remaining medium-risk customers
- `P3 monitor`: low-risk customers

## Business Impact Summary

- Active customers evaluated: `5,174`
- High-risk active customers: `595`
- P0/P1 active customers: `1,223`
- Active monthly revenue at risk: `110,603.66`
- Estimated net monthly retention impact: `19,662.01`
- Estimated annualized net retention impact: `235,944.12`

## Summary by Recommendation

| primary_recommendation | customers | avg_churn_probability | monthly_revenue_at_risk | estimated_net_mrr_impact | annualized_net_revenue_impact |
| --- | --- | --- | --- | --- | --- |
| customer support escalation | 1165 | 0.6291257552573428 | 53011.09 | 16577.81 | 198933.72 |
| monitor customer health | 3427 | 0.1392782618935922 | 29801.89 | 1732.61 | 20791.32 |
| engagement campaign | 141 | 0.5568367381936209 | 6634.08 | 1051.18 | 12614.16 |
| discount offer | 117 | 0.8245566269313007 | 8017.3099999999995 | 413.62 | 4963.44 |
| payment reminders | 54 | 0.575535257933976 | 2685.92 | 398.34 | 4780.08 |
| loyalty rewards | 67 | 0.5427439156849256 | 3351.09 | 147.02 | 1764.24 |
| onboarding assistance | 203 | 0.6163919095987246 | 7102.28 | -658.57 | -7902.84 |

## Summary by Risk Segment

| churn_risk_segment | customers | avg_churn_probability | monthly_revenue_at_risk | estimated_net_mrr_impact | annualized_net_revenue_impact |
| --- | --- | --- | --- | --- | --- |
| high risk | 595 | 0.8049487462746218 | 36986.59 | 7608.25 | 91299.0 |
| low risk | 3411 | 0.13724498075364902 | 29222.04 | 1705.04 | 20460.48 |
| medium risk | 1168 | 0.5399900551063157 | 44395.03 | 10348.72 | 124184.64 |

## Top Action Queue

| unified_customer_id | telco_customer_id | action_status | churn_label | predicted_churn_probability | predicted_churn_label | churn_risk_segment | retention_priority | customer_value_segment | monthly_charges | estimated_customer_lifetime_value | monthly_revenue_at_risk | primary_recommendation | secondary_recommendation | recommendation_reason | risk_driver_summary | expected_save_rate | estimated_action_cost | estimated_gross_mrr_saved | estimated_net_mrr_impact | annualized_net_revenue_impact | tenure | tenure_segment | contract | payment_method | payment_risk_score | inactivity_days | activity_status | engagement_score | customer_health_score | support_ticket_count | open_ticket_count | critical_ticket_count | low_satisfaction_ticket_count | complaint_frequency | support_burden_score | avg_satisfaction_rating | prediction_scope | best_model_name |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CUST0000296 | 0434-CSFON | active_retention | 0 | 0.8634063731692363 | 1 | high risk | P0 critical | high_value | 100.5 | 4723.5 | 86.77 | discount offer | payment method review | High churn probability combines with payment risk and price pressure. | low engagement, payment risk, valuable customer | 0.24 | 15.075 | 27.07 | 12.0 | 144.0 | 47 | 25_48_months | month_to_month | electronic_check | 1.0 | 114.0 | inactive_90_plus_days | 0.3806 | 0.5002 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 3.0 | full_model_scoring | logistic_regression |
| CUST0000092 | 0147-ESWWR | active_retention | 0 | 0.8260479477031462 | 1 | high risk | P0 critical | high_value | 101.25 | 3948.75 | 83.64 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | support friction, payment risk, valuable customer | 0.3 | 0.0 | 32.62 | 32.62 | 391.44 | 39 | 25_48_months | month_to_month | electronic_check | 1.0 | 1.0 | active_0_30_days | 0.486 | 0.4632 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 0.2498 | 3.0 | full_model_scoring | logistic_regression |
| CUST0006985 | 9912-OMZDS | active_retention | 0 | 0.7991607378537614 | 1 | high risk | P0 critical | high_value | 106.15 | 6262.85 | 84.83 | discount offer | payment method review | High churn probability combines with payment risk and price pressure. | payment risk, valuable customer | 0.24 | 15.9225 | 26.47 | 10.55 | 126.6 | 59 | 49_plus_months | one_year | electronic_check | 0.65 | 63.0 | active_31_90_days | 0.414 | 0.6085 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 3.0 | holdout_prediction_output | logistic_regression |
| CUST0001674 | 2439-LYPMQ | active_retention | 0 | 0.7951691512084516 | 1 | high risk | P0 critical | high_value | 102.6 | 3898.8 | 81.58 | discount offer | payment method review | High churn probability combines with payment risk and price pressure. | payment risk, valuable customer | 0.24 | 15.389999999999999 | 25.45 | 10.06 | 120.72 | 38 | 25_48_months | month_to_month | electronic_check | 1.0 | 46.0 | active_31_90_days | 0.4273 | 0.4928 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0293 | 3.0 | full_model_scoring | logistic_regression |
| CUST0004949 | 6968-GMKPR | active_retention | 0 | 0.787324111718725 | 1 | high risk | P0 critical | high_value | 81.55 | 4485.25 | 64.21 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | low engagement, support friction, payment risk, valuable customer | 0.3 | 0.0 | 25.04 | 25.04 | 300.48 | 55 | 49_plus_months | month_to_month | electronic_check | 1.0 | 588.0 | inactive_90_plus_days | 0.0939 | 0.3397 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 0.2498 | 3.0 | full_model_scoring | logistic_regression |
| CUST0005612 | 7901-TBKJX | active_retention | 0 | 0.786784448732347 | 1 | high risk | P0 critical | high_value | 101.05 | 5658.8 | 79.5 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | support friction, payment risk, valuable customer | 0.3 | 0.0 | 31.0 | 31.0 | 372.0 | 56 | 49_plus_months | month_to_month | electronic_check | 1.0 | 65.0 | active_31_90_days | 0.4111 | 0.4687 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 0.2498 | 3.0 | full_model_scoring | logistic_regression |
| CUST0001175 | 1728-CXQBE | active_retention | 0 | 0.7823095470450129 | 1 | high risk | P0 critical | high_value | 94.25 | 6032.0 | 73.73 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | support friction, payment risk, valuable customer | 0.3 | 0.0 | 28.75 | 28.75 | 345.0 | 64 | 49_plus_months | month_to_month | electronic_check | 1.0 | 58.0 | active_31_90_days | 0.4265 | 0.4769 | 2.0 | 2.0 | 0.0 | 0.0 | 1.0 | 0.3081 | 3.0 | holdout_prediction_output | logistic_regression |
| CUST0005687 | 8012-SOUDQ | active_retention | 0 | 0.7755132172689965 | 1 | high risk | P0 critical | high_value | 90.25 | 3880.75 | 69.99 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | low engagement, support friction, payment risk, valuable customer | 0.3 | 0.0 | 27.3 | 27.3 | 327.6 | 43 | 25_48_months | month_to_month | electronic_check | 1.0 | 333.0 | inactive_90_plus_days | 0.247 | 0.3759 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 0.2498 | 3.0 | full_model_scoring | logistic_regression |
| CUST0001189 | 1751-NCDLI | active_retention | 0 | 0.7727690014734838 | 1 | high risk | P0 critical | high_value | 98.85 | 4547.099999999999 | 76.39 | discount offer | payment method review | High churn probability combines with payment risk and price pressure. | payment risk, valuable customer | 0.24 | 14.827499999999999 | 23.83 | 9.0 | 108.0 | 46 | 25_48_months | month_to_month | electronic_check | 1.0 | 1.0 | active_0_30_days | 0.4924 | 0.5428 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 3.0 | full_model_scoring | logistic_regression |
| CUST0003946 | 5553-AOINX | active_retention | 0 | 0.7725815465775921 | 1 | high risk | P0 critical | high_value | 104.9 | 6923.400000000001 | 81.04 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | low engagement, support friction, payment risk, valuable customer | 0.3 | 0.0 | 31.61 | 31.61 | 379.32 | 66 | 49_plus_months | one_year | electronic_check | 0.65 | 216.0 | inactive_90_plus_days | 0.319 | 0.5227 | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 0.2498 | 3.0 | full_model_scoring | logistic_regression |
| CUST0001681 | 2452-KDRRH | active_retention | 0 | 0.7712942118806341 | 1 | high risk | P0 critical | high_value | 101.4 | 6793.8 | 78.21 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | low engagement, support friction, valuable customer | 0.3 | 0.0 | 30.5 | 30.5 | 366.0 | 67 | 49_plus_months | month_to_month | credit_card_automatic | 0.55 | 137.0 | inactive_90_plus_days | 0.3691 | 0.575 | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.2088 | 3.0 | full_model_scoring | logistic_regression |
| CUST0002778 | 3951-NJCVI | active_retention | 0 | 0.763746044536866 | 1 | high risk | P0 critical | high_value | 95.05 | 3992.1 | 72.59 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | support friction, payment risk, valuable customer | 0.3 | 0.0 | 28.31 | 28.31 | 339.72 | 42 | 25_48_months | month_to_month | electronic_check | 1.0 | 6.0 | active_0_30_days | 0.4534 | 0.4418 | 2.0 | 2.0 | 0.0 | 0.0 | 1.0 | 0.3081 | 3.0 | holdout_prediction_output | logistic_regression |
| CUST0000685 | 1013-QCWAM | active_retention | 0 | 0.7582520171778568 | 1 | high risk | P0 critical | high_value | 100.8 | 6652.8 | 76.43 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | support friction, payment risk, valuable customer | 0.3 | 0.0 | 29.81 | 29.81 | 357.72 | 66 | 49_plus_months | month_to_month | electronic_check | 1.0 | 10.0 | active_0_30_days | 0.4449 | 0.5462 | 1.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0769 | 5.0 | full_model_scoring | logistic_regression |
| CUST0003792 | 5331-RGMTT | active_retention | 0 | 0.7551789235124767 | 1 | high risk | P0 critical | high_value | 99.05 | 5348.7 | 74.8 | customer support escalation | service recovery follow-up | Support friction is visible through open, critical, complaint, or low satisfaction signals. | low engagement, support friction, valuable customer | 0.3 | 0.0 | 29.17 | 29.17 | 350.04 | 54 | 49_plus_months | month_to_month | credit_card_automatic | 0.55 | 262.0 | inactive_90_plus_days | 0.2911 | 0.5591 | 1.0 | 0.0 | 0.0 | 0.0 | 1.0 | 0.0392 | 3.0 | full_model_scoring | logistic_regression |
| CUST0005332 | 7529-ZDFXI | active_retention | 0 | 0.7533204269401907 | 1 | high risk | P0 critical | high_value | 89.85 | 5121.45 | 67.69 | discount offer | payment method review | High churn probability combines with payment risk and price pressure. | payment risk, valuable customer | 0.24 | 13.4775 | 21.12 | 7.64 | 91.68 | 57 | 49_plus_months | month_to_month | electronic_check | 1.0 | 1.0 | active_0_30_days | 0.5232 | 0.578 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 3.0 | full_model_scoring | logistic_regression |

## Business Reasoning

- Discount offers are reserved for customers where risk combines with payment
  risk and price pressure, because discounts carry margin cost.
- Onboarding assistance is used for early-tenure or low-health customers where
  the likely issue is value realization rather than price alone.
- Support escalation is prioritized when complaints, open tickets, critical
  tickets, or low satisfaction indicate service friction.
- Payment reminders and billing reviews are targeted to customers with
  electronic check or elevated payment-risk behavior.
- Engagement campaigns are recommended when inactivity or low engagement is the
  clearest churn signal.
- Loyalty rewards are aimed at valuable customers whose risk is meaningful but
  whose issue does not point to a support or billing recovery path.

## Outputs

- `data/processed/customer_retention_actions.csv`
- `reports/business_reports/customer_retention_actions.csv`
- `reports/business_reports/retention_recommendation_report.md`
- `reports/business_reports/retention_summary_by_risk.csv`
- `reports/business_reports/retention_summary_by_recommendation.csv`
- `reports/business_reports/retention_summary_by_priority.csv`
