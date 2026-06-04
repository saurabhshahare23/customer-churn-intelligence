# Churn Feature Engineering Workflow

## Purpose

This workflow creates a production-style, ML-ready customer churn feature table
from the cleaned and unified datasets. It focuses only on feature engineering,
not model training.

## Inputs

- `data/processed/customers_cleaned.csv`
- `data/processed/customer_activity_cleaned.csv`
- `data/processed/support_interactions_cleaned.csv`

## Outputs

All outputs are saved to `data/processed/`:

- `churn_features_master.csv`
- `churn_features_master_pre_encoding.csv`
- `churn_feature_dictionary.csv`
- `churn_feature_correlation_matrix.csv`
- `churn_feature_target_correlations.csv`
- `churn_feature_outlier_audit.csv`
- `churn_feature_encoding_manifest.csv`
- `churn_feature_engineering_report.md`

## Analytical Grain

The final table is one row per `unified_customer_id`.

`churn_label` is the supervised learning target retained for future modeling.
The row identifier `unified_customer_id` is retained for traceability and should
be excluded from model predictors.

## Feature Groups

### Customer and Subscription Features

These include tenure, senior citizen flag, contract type, internet service,
paperless billing, payment method, service-plan indicators, and derived tenure
segments.

### Revenue and Value Features

Features include:

- `avg_monthly_spend`
- `estimated_customer_lifetime_value`
- `monthly_charge_to_tenure_ratio`
- `customer_value_segment`
- `monthly_spend_per_invoice`

### Behavioral Features

Activity data is aggregated into:

- `inactivity_days`
- `invoice_count`
- `activity_line_count`
- `active_day_count`
- `distinct_product_count`
- `return_rate`
- `recency_frequency_metrics`
- `engagement_score`

### Support and Complaint Features

Support interactions are aggregated into:

- `support_ticket_count`
- `open_ticket_count`
- `critical_ticket_count`
- `low_satisfaction_ticket_count`
- `complaint_frequency`
- `support_burden_score`
- `avg_resolution_hours`
- `support_to_tenure_ratio`
- `complaints_per_tenure_month`

### Risk and Health Scores

The workflow creates transparent analytical scores:

- `payment_risk_score`
- `support_burden_score`
- `engagement_score`
- `customer_health_score`

These are feature inputs and business diagnostics, not trained model outputs.

## Missing Value Handling

- Missing total charges are imputed with `monthly_charges * tenure`.
- Customers without activity receive zero activity metrics and zero engagement.
- Customers without support history receive zero support metrics and neutral
  satisfaction values.
- Rate features use protected denominators to avoid infinite values.
- Missing categorical values are encoded explicitly.

## Encoding

Categorical features are one-hot encoded with pandas. An encoding manifest is
saved so downstream modeling work can inspect which categories were expanded.

## Outlier Handling

High-variance continuous features are capped at the 1st and 99th percentiles.
An audit file records the lower cap, upper cap, and number of values capped for
each feature.

## Leakage Controls

The final ML-ready dataset removes:

- Raw churn text labels
- Source customer identifiers
- Source lineage columns
- Date timestamp columns
- Free-text fields

The target remains as `churn_label`.

## Run Command

From the project root:

```bash
python src/feature_engineering/build_churn_features.py
```
