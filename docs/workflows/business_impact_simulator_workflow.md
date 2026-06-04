# Business Impact Simulator Workflow

## Purpose

This workflow estimates the financial impact of churn and retention campaigns.
It is designed for executive decision-making, campaign planning, and business
intelligence review.

No dashboards are built in this stage.

## Inputs

- `models/model_metrics/best_model_test_predictions.csv`
- `reports/business_reports/customer_retention_actions.csv`
- `data/processed/churn_features_master.csv`

## Outputs

All tabular outputs are saved to `reports/business_reports/`:

- `business_impact_kpi_summary.csv`
- `business_impact_scenario_summary.csv`
- `business_impact_by_value_segment.csv`
- `business_impact_by_risk_segment.csv`
- `business_impact_by_recommendation.csv`
- `top_revenue_at_risk_customers.csv`
- `business_impact_simulator_report.md`

Figures are saved to `reports/figures/`:

- `business_impact_revenue_at_risk_by_segment.png`
- `business_impact_revenue_saved_by_scenario.png`
- `business_impact_roi_by_scenario.png`
- `business_impact_customer_segment_clv_at_risk.png`

## Financial Metrics

The simulator calculates:

- Revenue at risk
- Estimated revenue loss from churn
- Revenue recovery potential
- Customer lifetime value at risk
- Net recovery after estimated campaign cost
- Annualized financial impact

## Scenario Design

The simulator evaluates active high-risk customers only:

- Scenario A: retain top 5% high-risk customers
- Scenario B: retain top 10% high-risk customers
- Scenario C: retain top 20% high-risk customers

High-risk customers are ranked by churn probability, monthly revenue at risk,
and customer lifetime value.

## Business Assumptions

- Revenue at risk is probability-weighted monthly recurring revenue exposure.
- Revenue saved is based on the expected save rate from the retention action.
- ROI is calculated as net monthly revenue saved divided by campaign cost.
- CLV protected is directional and should be treated as a planning estimate.
- Results support prioritization, not finance-approved forecasting.

## Run Command

From the project root:

```bash
python src/evaluation/business_impact_simulator.py
```
