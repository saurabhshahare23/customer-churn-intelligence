# Data Cleaning and Customer Mapping Run Report

## Scope

This run cleans the three raw customer churn analytics sources and creates a
single join key named `unified_customer_id`. No machine learning or feature
engineering is performed in this workflow.

## Important Transformations

- Raw files are loaded from `data/raw` with pandas and are never modified.
- Column names are standardized to lower snake case for warehouse compatibility.
- Text fields are trimmed and repeated whitespace is collapsed.
- Categorical fields are standardized to lower snake case values.
- Date fields are parsed with `pd.to_datetime(..., errors="coerce")` so invalid dates become auditable nulls.
- Numeric fields are explicitly cast with `pd.to_numeric(..., errors="coerce")`.
- Exact duplicate activity rows are removed before assigning activity line ids.
- Invalid or analytically important conditions are retained as flags instead of silently deleting records.
- `unified_customer_id` is the canonical customer key across all cleaned outputs.

## Synthetic Customer Mapping Strategy

The source systems do not share a governed customer identifier, so this workflow
uses deterministic synthetic identity rules:

- Telco churn records receive a canonical `unified_customer_id` directly from their native `telco_customer_id`.
- Known activity `source_activity_customer_id` values are mapped one-to-one into the Telco customer pool by stable sorted rank.
- Activity rows with missing customer ids are mapped by deterministic invoice hash and receive a lower confidence score.
- Support customer emails are lowercased and mapped by deterministic email hash within a demographic segment when gender and senior status can be inferred.
- Every mapping is written to `customer_identity_bridge.csv` with its method and confidence score.

These mappings are appropriate for an analytics portfolio project where the
goal is to demonstrate cross-source integration. In a production business
environment, the bridge should be replaced or validated with governed CRM,
billing account, or consented identity data.

## Dataset Quality Summary

| dataset | stage | row_count | column_count | duplicate_row_count | missing_cell_count |
| --- | --- | --- | --- | --- | --- |
| telco | raw | 7043 | 21 | 0 | 0 |
| telco | standardized_raw_columns | 7043 | 21 | 0 | 0 |
| activity | raw | 1067371 | 8 | 34335 | 247389 |
| activity | standardized_raw_columns | 1067371 | 8 | 34335 | 247389 |
| support | raw | 8469 | 17 | 0 | 19919 |
| support | standardized_raw_columns | 8469 | 17 | 0 | 19919 |
| customers_cleaned | cleaned | 7043 | 27 | 0 | 11 |
| customer_activity_cleaned | cleaned | 1033036 | 17 | 0 | 239426 |
| support_interactions_cleaned | cleaned | 8469 | 28 | 0 | 25619 |
| customer_identity_bridge | cleaned | 30057 | 8 | 0 | 51794 |

## Identity Method Summary

| source_system | identity_resolution_method | identity_count |
| --- | --- | --- |
| customer_activity | synthetic_invoice_hash_for_missing_customer | 8752 |
| customer_activity | synthetic_ranked_activity_customer_id | 5942 |
| support_tickets | synthetic_email_hash_demographic_segment | 5684 |
| support_tickets | synthetic_email_hash_global_pool | 2636 |
| telco_customer_churn | native_telco_customer_id | 7043 |

## Cleaned Outputs

- `customers_cleaned.csv`
- `customer_activity_cleaned.csv`
- `support_interactions_cleaned.csv`
- `customer_identity_bridge.csv`
- `data_quality_summary.csv`
- `data_quality_profile.csv`
