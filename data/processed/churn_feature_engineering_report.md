# Churn Feature Engineering Report

## Scope

This workflow creates an ML-ready churn feature dataset from the cleaned
customer, activity, and support interaction tables. It does not train models.

## Analytical Grain

The master dataframe is one row per `unified_customer_id`.

- Pre-encoding master shape: `7,043` rows x `95` columns
- Final ML-ready shape: `7,043` rows x `197` columns
- Target column: `churn_label`

## Major Feature Groups

- Customer subscription and tenure features
- Payment and contract risk features
- Revenue and customer value indicators
- Activity recency, frequency, monetary, return, and engagement features
- Support burden, complaint, dissatisfaction, and resolution features
- Composite health, engagement, support, and payment scores

## Feature Dictionary

| feature_name | business_definition | feature_family |
| --- | --- | --- |
| inactivity_days | Days since the customer's last mapped activity event. | Behavioral recency |
| engagement_score | Weighted recency, frequency, and monetary activity score scaled from 0 to 1. | Engagement |
| support_burden_score | Composite score based on ticket volume, open tickets, critical issues, low satisfaction, and resolution time. | Support friction |
| payment_risk_score | Transparent score using electronic check, month-to-month contract, and paperless billing indicators. | Payment and contract risk |
| complaint_frequency | Share of support tickets that represent complaints, refund, cancellation, billing, or technical issues. | Complaint behavior |
| avg_monthly_spend | Historical total charges divided by tenure, with monthly charges used for zero-tenure customers. | Revenue |
| customer_value_segment | Quartile segment based on estimated customer lifetime value. | Value segmentation |
| recency_frequency_metrics | Weighted score combining activity recency and invoice frequency. | Behavioral RFM |
| estimated_customer_lifetime_value | Monthly charges multiplied by tenure. | CLV indicator |
| customer_health_score | Composite health score combining engagement, support burden, payment risk, and tenure. | Customer health |
| support_to_tenure_ratio | Support tickets normalized by customer tenure. | Support intensity |
| complaints_per_tenure_month | Complaint ticket count normalized by customer tenure. | Complaint intensity |
| return_rate | Share of activity lines marked as returns. | Activity quality |
| monthly_spend_per_invoice | Average monthly spend divided by invoice count, with fallback to average monthly spend. | Revenue engagement |

## Missing Value Handling

- Missing `total_charges` values are imputed with `monthly_charges * tenure`.
- Customers without activity receive zero activity counts, revenue metrics, and engagement scores.
- Customers without support history receive zero support counts and neutral satisfaction values.
- Rate features divide by protected denominators to avoid infinite values.
- Categorical missing values are encoded explicitly with one-hot `nan` columns.

## Outlier Handling

Continuous high-variance features are capped at the 1st and 99th percentiles.
This keeps extreme transactions from dominating future model training while
preserving customer rows.

| feature | lower_cap_p01 | upper_cap_p99 | values_capped_low | values_capped_high |
| --- | --- | --- | --- | --- |
| monthly_charges | 19.2 | 114.729 | 65 | 71 |
| total_charges | 19.9 | 8039.882999999997 | 69 | 71 |
| total_charges_imputed | 19.75 | 8039.255999999999 | 65 | 71 |
| avg_monthly_spend | 17.623475 | 115.02070422535212 | 71 | 71 |
| estimated_customer_lifetime_value | 19.75 | 8038.8 | 65 | 70 |
| monthly_charge_to_tenure_ratio | 0.28903772378516623 | 40.20799999999999 | 71 | 71 |
| activity_line_count | 0.0 | 1076.58 | 0 | 71 |
| invoice_count | 0.0 | 55.0 | 0 | 70 |
| total_quantity | -979.0799999999999 | 14290.499999999987 | 71 | 71 |
| net_activity_revenue | -448.7488 | 25488.032 | 71 | 71 |
| gross_activity_revenue | 0.0 | 26272.507999999998 | 0 | 71 |
| return_amount | 0.0 | 3636.2729999999992 | 0 | 71 |
| avg_invoice_value | -196.44899999999998 | 2238.6048 | 71 | 71 |
| avg_unit_price | 0.0 | 227.67439999999712 | 0 | 68 |
| distinct_product_count | 0.0 | 611.5799999999999 | 0 | 71 |
| support_ticket_count | 0.0 | 4.0 | 0 | 67 |
| avg_resolution_hours | -16.991333333333337 | 17.926333333333336 | 71 | 71 |
| max_resolution_hours | -16.912333333333336 | 18.509666666666664 | 71 | 71 |
| support_to_tenure_ratio | 0.0 | 1.5 | 0 | 28 |
| complaints_per_tenure_month | 0.0 | 1.0 | 0 | 59 |
| monthly_spend_per_invoice | 0.682296568627451 | 105.75247101449276 | 71 | 71 |

## Encoding Strategy

Categorical variables are one-hot encoded after leakage columns are removed.
The target remains numeric and is not encoded.

| source_column | encoding | category_count | categories |
| --- | --- | --- | --- |
| gender | one_hot | 2 | female, male |
| partner | one_hot | 2 | no, yes |
| dependents | one_hot | 2 | no, yes |
| phone_service | one_hot | 2 | no, yes |
| multiple_lines | one_hot | 3 | no, no_phone_service, yes |
| internet_service | one_hot | 3 | dsl, fiber_optic, no |
| online_security | one_hot | 3 | no, no_internet_service, yes |
| online_backup | one_hot | 3 | no, no_internet_service, yes |
| device_protection | one_hot | 3 | no, no_internet_service, yes |
| tech_support | one_hot | 3 | no, no_internet_service, yes |
| streaming_tv | one_hot | 3 | no, no_internet_service, yes |
| streaming_movies | one_hot | 3 | no, no_internet_service, yes |
| contract | one_hot | 3 | month_to_month, one_year, two_year |
| paperless_billing | one_hot | 2 | no, yes |
| payment_method | one_hot | 4 | bank_transfer_automatic, credit_card_automatic, electronic_check, mailed_check |
| customer_value_segment | one_hot | 4 | emerging_value, established_value, high_value, low_value |
| tenure_segment | one_hot | 5 | 0_6_months, 13_24_months, 25_48_months, 49_plus_months, 7_12_months |
| primary_activity_country | one_hot | 42 | Australia, Austria, Bahrain, Belgium, Bermuda, Brazil, Canada, Channel Islands, Cyprus, Czech Republic, Denmark, Eire, European Community, Finland, France, Germany, Greece, Hong Kong, Iceland, Israel, Italy, Japan, Korea, Lebanon, Lithuania, Malta, Netherlands, Norway, Poland, Portugal |
| primary_ticket_type | one_hot | 5 | billing_inquiry, cancellation_request, product_inquiry, refund_request, technical_issue |
| primary_ticket_priority | one_hot | 4 | critical, high, low, medium |
| primary_ticket_channel | one_hot | 4 | chat, email, phone, social_media |
| activity_status | one_hot | 4 | active_0_30_days, active_31_90_days, inactive_90_plus_days, no_activity |

## Leakage Controls

The workflow removes raw labels, natural source identifiers, date timestamps,
free-text fields, and lineage-only fields from the final ML-ready dataset.
`unified_customer_id` is retained only as a row identifier, not as a predictive
feature.

## Strongest Target Correlations

These correlations are descriptive diagnostics, not model results.

| feature | correlation_with_churn_label |
| --- | --- |
| payment_risk_score | 0.4357096449400812 |
| monthly_charge_to_tenure_ratio | 0.4195853063192062 |
| contract_month_to_month | 0.4051029106879898 |
| is_month_to_month_contract | 0.4051029106879898 |
| customer_health_score | -0.38763448941464407 |
| tenure | -0.3522286701130792 |
| online_security_no | 0.3426367998511234 |
| no_online_security_flag | 0.3426367998511234 |
| tech_support_no | 0.3372807277351978 |
| no_tech_support_flag | 0.3372807277351978 |
| tenure_segment_0_6_months | 0.3085385026607783 |
| internet_service_fiber_optic | 0.30801974494482387 |
| contract_two_year | -0.30225346934964975 |
| is_electronic_check | 0.3019187490112847 |
| payment_method_electronic_check | 0.3019187490112847 |

## Outputs

- `data/processed/churn_features_master.csv`
- `data/processed/churn_features_master_pre_encoding.csv`
- `data/processed/churn_feature_dictionary.csv`
- `data/processed/churn_feature_correlation_matrix.csv`
- `data/processed/churn_feature_target_correlations.csv`
- `data/processed/churn_feature_outlier_audit.csv`
- `data/processed/churn_feature_encoding_manifest.csv`
