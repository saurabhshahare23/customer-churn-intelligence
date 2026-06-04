# Business Impact Simulator Report

## Scope

This simulator estimates the financial impact of churn and retention campaigns
using churn predictions, customer retention actions, and the final feature
master. It supports decision-making around where retention spend should be
focused. No dashboards are built.

## Inputs

- `models/model_metrics/best_model_test_predictions.csv`
- `reports/business_reports/customer_retention_actions.csv`
- `data/processed/churn_features_master.csv`

## Executive KPI Summary

| kpi | value | business_definition |
| --- | --- | --- |
| customers_scored | 7043.0 | All customers scored by the saved churn model. |
| active_customers_evaluated | 5174.0 | Customers eligible for retention actions. |
| holdout_prediction_rows_loaded | 1409.0 | Rows loaded from model holdout prediction output. |
| active_high_risk_customers | 595.0 | Active customers with churn probability >= 0.70. |
| monthly_revenue_at_risk | 110603.66 | Probability-weighted monthly revenue exposure. |
| annual_revenue_at_risk | 1327243.92 | Probability-weighted annual revenue exposure. |
| customer_lifetime_value_at_risk | 3391722.31 | Probability-weighted CLV exposure. |
| monthly_recovery_potential | 24054.73 | Estimated gross monthly revenue recoverable from recommended actions. |
| net_monthly_recovery_potential | 19662.01 | Gross recovery less estimated action cost. |
| annualized_net_recovery_potential | 235944.12 | Annualized net recovery potential. |

## Scenario Summary

| scenario | scenario_description | target_high_risk_pct | high_risk_pool_customers | customers_targeted | expected_customers_saved | retention_effectiveness_pct | monthly_revenue_at_risk_targeted | gross_monthly_revenue_saved | campaign_cost | net_monthly_revenue_saved | annualized_net_revenue_saved | customer_lifetime_value_protected | estimated_roi_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Scenario A | Retain top 5% high-risk customers | 0.05 | 595 | 30 | 8.58 | 28.6 | 2300.94 | 542.44 | 79.58 | 462.86 | 5554.32 | 1796.09 | 581.61 |
| Scenario B | Retain top 10% high-risk customers | 0.1 | 595 | 60 | 17.0 | 28.33 | 4397.42 | 1057.96 | 182.08 | 875.9 | 10510.8 | 4800.22 | 481.07 |
| Scenario C | Retain top 20% high-risk customers | 0.2 | 595 | 119 | 33.32 | 28.0 | 8473.25 | 2041.81 | 431.64 | 1610.21 | 19322.52 | 11793.7 | 373.05 |

The strongest scenario by net monthly revenue saved is **Scenario C**
with estimated net monthly savings of **1,610.21**
and annualized net savings of **19,322.52**.

## Segment Impact

### By Risk Segment

| churn_risk_segment | customers | avg_churn_probability | monthly_revenue_at_risk | expected_clv_at_risk | net_monthly_recovery_potential | annualized_recovery_potential |
| --- | --- | --- | --- | --- | --- | --- |
| medium risk | 1168 | 0.5399900551063157 | 44395.03 | 1468809.24 | 10348.72 | 124184.64 |
| high risk | 595 | 0.8049487462746218 | 36986.59 | 556874.43 | 7608.25 | 91299.0 |
| low risk | 3411 | 0.13724498075364897 | 29222.04 | 1366038.64 | 1705.04 | 20460.48 |

### By Customer Value Segment

| customer_value_segment | customers | avg_churn_probability | monthly_revenue_at_risk | expected_clv_at_risk | net_monthly_recovery_potential | annualized_recovery_potential |
| --- | --- | --- | --- | --- | --- | --- |
| high_value | 1506 | 0.23616674297385967 | 34830.16 | 2031413.55 | 6712.66 | 80551.92 |
| established_value | 1354 | 0.30412234854257814 | 32538.19 | 1003124.27 | 6817.14 | 81805.68000000001 |
| emerging_value | 1310 | 0.2685684544821079 | 22240.5 | 289479.96 | 3655.75 | 43869.0 |
| low_value | 1004 | 0.4566952863858849 | 20994.81 | 67704.53 | 2476.46 | 29717.52 |

### By Recommendation Type

| primary_recommendation | customers | avg_churn_probability | monthly_revenue_at_risk | campaign_cost | net_monthly_recovery_potential | annualized_recovery_potential |
| --- | --- | --- | --- | --- | --- | --- |
| customer support escalation | 1165 | 0.6291257552573428 | 53011.09 | 0.0 | 16577.81 | 198933.72 |
| monitor customer health | 3427 | 0.13927826189359216 | 29801.89 | 0.0 | 1732.61 | 20791.32 |
| engagement campaign | 141 | 0.5568367381936209 | 6634.08 | 352.5 | 1051.18 | 12614.16 |
| discount offer | 117 | 0.8245566269313007 | 8017.3099999999995 | 1460.76 | 413.62 | 4963.44 |
| payment reminders | 54 | 0.575535257933976 | 2685.92 | 54.0 | 398.34 | 4780.08 |
| loyalty rewards | 67 | 0.5427439156849256 | 3351.09 | 495.58 | 147.02 | 1764.24 |
| onboarding assistance | 203 | 0.6163919095987246 | 7102.28 | 2030.0 | -658.57 | -7902.84 |

## Business Interpretation

- Revenue at risk is probability-weighted monthly revenue exposure. It is not a
  booked loss; it is a prioritization signal.
- Estimated revenue loss annualizes the monthly exposure to make the churn
  problem visible in planning terms.
- Recovery potential uses the recommended action's expected save rate and
  estimated cost, making it useful for campaign prioritization.
- Customer lifetime value impact shows where near-term churn risk intersects
  with longer-term account value.
- The 5%, 10%, and 20% high-risk scenarios help leaders compare focused
  intervention against broader campaign scale.

## Decision Guidance

- Start with the highest ROI scenario when retention capacity is limited.
- Use the 10% scenario when the team can handle a broader but still focused
  campaign.
- Use the 20% scenario when the business objective is revenue defense and the
  operation can absorb more outreach volume.
- Review negative or low-ROI action types before funding them; they may still be
  appropriate for strategic accounts but should not be treated as automatic.

## Headline Financial View

- Active monthly revenue at risk: `110,603.66`
- Active annual revenue at risk: `1,327,243.92`
- Customer lifetime value at risk: `3,391,722.31`
- Net monthly recovery potential: `19,662.01`
- Annualized net recovery potential: `235,944.12`

## Outputs

- `reports/business_reports/business_impact_kpi_summary.csv`
- `reports/business_reports/business_impact_scenario_summary.csv`
- `reports/business_reports/business_impact_by_value_segment.csv`
- `reports/business_reports/business_impact_by_risk_segment.csv`
- `reports/business_reports/business_impact_by_recommendation.csv`
- `reports/business_reports/top_revenue_at_risk_customers.csv`
- `reports/business_reports/business_impact_simulator_report.md`
- `reports/figures/business_impact_revenue_at_risk_by_segment.png`
- `reports/figures/business_impact_revenue_saved_by_scenario.png`
- `reports/figures/business_impact_roi_by_scenario.png`
- `reports/figures/business_impact_customer_segment_clv_at_risk.png`
