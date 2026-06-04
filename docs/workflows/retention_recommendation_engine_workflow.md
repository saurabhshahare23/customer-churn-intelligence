# Retention Recommendation Engine Workflow

## Purpose

This workflow converts churn model outputs and customer features into actionable
retention recommendations. It is designed for customer analytics, retention
operations, and business stakeholder review.

No dashboards are built in this stage.

## Inputs

- `data/processed/churn_features_master.csv`
- `data/processed/churn_features_master_pre_encoding.csv`
- `models/model_metrics/best_model_test_predictions.csv`
- `models/trained_models/best_churn_model.joblib`

## Outputs

- `data/processed/customer_retention_actions.csv`
- `reports/business_reports/customer_retention_actions.csv`
- `reports/business_reports/retention_recommendation_report.md`
- `reports/business_reports/retention_summary_by_risk.csv`
- `reports/business_reports/retention_summary_by_recommendation.csv`
- `reports/business_reports/retention_summary_by_priority.csv`

## Workflow Steps

1. Load the final feature table and readable pre-encoding feature table.
2. Load holdout prediction outputs and the saved best churn model package.
3. Score every customer with the saved model so the action table covers the full
   customer base, not only the test split.
4. Assign risk segments from churn probability.
5. Apply transparent business rules using inactivity, complaints, support
   burden, payment behavior, engagement, tenure, and customer value.
6. Assign retention priority levels.
7. Estimate monthly revenue at risk, action cost, expected saved revenue, and
   annualized net impact.
8. Save customer-level actions and executive summary tables.

## Risk Segments

- Low risk: churn probability below `0.40`
- Medium risk: churn probability from `0.40` to below `0.70`
- High risk: churn probability `0.70` or higher

## Recommendation Types

- `discount offer`
- `onboarding assistance`
- `loyalty rewards`
- `customer support escalation`
- `payment reminders`
- `engagement campaign`
- `monitor customer health`

## Priority Levels

- `P0 critical`: high-risk and high-value active customers
- `P1 high`: high-risk customers or medium-risk valuable customers
- `P2 medium`: remaining medium-risk customers
- `P3 monitor`: low-risk customers

## Business Impact Logic

The impact estimate is intentionally directional. It combines:

- Predicted churn probability
- Monthly charges
- Expected save rate by intervention
- Customer value multiplier
- Estimated action cost

This creates a prioritization metric, not a finance-approved forecast.

## Run Command

From the project root:

```bash
python src/recommendation_engine/build_retention_recommendations.py
```
