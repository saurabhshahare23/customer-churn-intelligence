# Customer Churn Analytical Data Architecture

## 1. Objective

This document defines the analytical data architecture for an industry-level customer churn analytics project using three raw datasets:

- `telco_customer_churn.csv`
- `customer_activity.csv`
- `support_tickets.csv`

The goal at this stage is schema design, analytical modeling, and feature-table planning. Model training is intentionally out of scope.

## 2. Load Raw Datasets With Pandas

```python
from pathlib import Path
import pandas as pd

RAW_DIR = Path("../../data/raw")

telco = pd.read_csv(RAW_DIR / "telco_customer_churn.csv")
activity = pd.read_csv(RAW_DIR / "customer_activity.csv")
support = pd.read_csv(RAW_DIR / "support_tickets.csv")

datasets = {
    "telco_customer_churn": telco,
    "customer_activity": activity,
    "support_tickets": support,
}

for name, df in datasets.items():
    print(f"\n{name}: {df.shape}")
    display(df.head())
    display(pd.DataFrame({
        "column": df.columns,
        "dtype": [df[c].dtype for c in df.columns],
        "null_count": [df[c].isna().sum() for c in df.columns],
        "unique_count": [df[c].nunique(dropna=True) for c in df.columns],
    }))
```

## 3. Source Dataset Inspection

### 3.1 `telco_customer_churn.csv`

Shape: `7,043 rows x 21 columns`

Business purpose:

This is the primary churn-labeled customer subscription dataset. It describes customer demographics, contracted services, payment behavior, tenure, charges, and the churn target.

Important columns:

| Column | Purpose |
|---|---|
| `customerID` | Natural customer identifier inside the telco source system |
| `gender`, `SeniorCitizen`, `Partner`, `Dependents` | Demographic attributes |
| `tenure` | Customer tenure in months |
| `PhoneService`, `InternetService`, add-on service columns | Product and service subscription attributes |
| `Contract`, `PaperlessBilling`, `PaymentMethod` | Commercial and billing attributes |
| `MonthlyCharges`, `TotalCharges` | Monetary attributes |
| `Churn` | Churn label |

Possible identifiers:

- Primary candidate key: `customerID`
- `customerID` has `7,043` unique values across `7,043` rows, so it is unique in this source.

Granularity:

- One row per telco customer subscription snapshot.

### 3.2 `customer_activity.csv`

Shape: `1,067,371 rows x 8 columns`

Business purpose:

This dataset captures customer purchase or transaction activity at invoice-line level. It can be used to engineer behavioral features such as recency, frequency, monetary value, order volume, product diversity, returns, and country-level activity.

Important columns:

| Column | Purpose |
|---|---|
| `Invoice` | Transaction or invoice identifier |
| `StockCode` | Product SKU or stock identifier |
| `Description` | Product description |
| `Quantity` | Quantity purchased or returned |
| `InvoiceDate` | Transaction timestamp |
| `Price` | Unit price |
| `Customer ID` | Source customer identifier, nullable |
| `Country` | Customer or transaction country |

Possible identifiers:

- Candidate customer identifier: `Customer ID`
- Candidate transaction identifier: `Invoice`
- Candidate line grain: `Invoice` + `StockCode` + line occurrence
- `Customer ID` has `243,007` null values, so anonymous transactions must be handled explicitly.
- `Invoice` repeats because the dataset is invoice-line level.

Granularity:

- One row per invoice line item.

### 3.3 `support_tickets.csv`

Shape: `8,469 rows x 17 columns`

Business purpose:

This dataset captures customer support interactions and service experience. It can be used to engineer customer-friction features such as ticket count, open-ticket count, priority mix, time to first response, time to resolution, channel mix, issue type, and satisfaction.

Important columns:

| Column | Purpose |
|---|---|
| `Ticket ID` | Natural ticket identifier |
| `Customer Name`, `Customer Email` | Customer identity attributes from support system |
| `Customer Age`, `Customer Gender` | Customer profile attributes in support system |
| `Product Purchased`, `Date of Purchase` | Product context |
| `Ticket Type`, `Ticket Subject`, `Ticket Priority`, `Ticket Channel` | Support classification attributes |
| `Ticket Status` | Current ticket lifecycle status |
| `First Response Time`, `Time to Resolution` | Service responsiveness timestamps |
| `Customer Satisfaction Rating` | Post-resolution satisfaction signal |

Possible identifiers:

- Primary candidate key: `Ticket ID`
- Customer identity candidates: `Customer Email`, `Customer Name`
- `Ticket ID` is unique.
- `Customer Email` is a stronger customer identifier than `Customer Name`, but it is still source-specific and cannot directly join to telco `customerID` without an identity bridge.

Granularity:

- One row per support ticket.

## 4. Identity Resolution Strategy

The three datasets do not share a single confirmed customer key:

| Source | Customer identifier |
|---|---|
| Telco churn | `customerID` |
| Customer activity | `Customer ID` |
| Support tickets | `Customer Email`, `Customer Name` |

Industry best practice is to avoid forced joins across unrelated identifiers. Instead, create a canonical customer dimension and a source identity mapping table.

Recommended identity model:

| Table | Purpose |
|---|---|
| `dim_customer` | One canonical customer row per resolved customer |
| `bridge_customer_identity` | Maps source-specific identifiers to canonical `customer_key` |

Initial implementation rule:

- Every unique source customer identifier becomes a row in `bridge_customer_identity`.
- If no trusted matching logic exists between source systems, assign separate `customer_key` values by source.
- Later, deterministic or probabilistic matching can merge identities using verified email, CRM IDs, billing account IDs, or governed matching rules.

## 5. Proposed Relational Analytical Structure

### 5.1 Dimension Tables

#### `dim_customer`

Purpose:

Canonical customer entity used across analytical marts.

Primary key:

- `customer_key` surrogate key

Candidate attributes:

- `customer_key`
- `first_seen_date`
- `latest_seen_date`
- `customer_source_count`
- `is_identity_resolved`

Granularity:

- One row per canonical customer.

#### `bridge_customer_identity`

Purpose:

Maps source-specific customer identifiers to the canonical customer key.

Primary key:

- `customer_identity_key` surrogate key

Foreign key:

- `customer_key` references `dim_customer.customer_key`

Candidate attributes:

- `customer_identity_key`
- `customer_key`
- `source_system`
- `source_customer_id`
- `source_customer_email`
- `source_customer_name`
- `is_primary_identity`
- `identity_confidence_score`

Granularity:

- One row per customer identifier per source system.

#### `dim_product`

Purpose:

Conformed product dimension for activity and support product context.

Primary key:

- `product_key` surrogate key

Candidate natural keys:

- `StockCode` from activity
- `Product Purchased` from support

Granularity:

- One row per product or SKU after standardization.

#### `dim_date`

Purpose:

Reusable calendar dimension for invoices, purchases, responses, resolutions, and churn snapshots.

Primary key:

- `date_key`, usually integer `YYYYMMDD`

Granularity:

- One row per calendar date.

#### `dim_contract`

Purpose:

Stores telco contract and billing plan categories.

Primary key:

- `contract_key`

Granularity:

- One row per unique combination of `Contract`, `PaperlessBilling`, and `PaymentMethod`.

#### `dim_service_plan`

Purpose:

Stores telco service subscription attributes.

Primary key:

- `service_plan_key`

Granularity:

- One row per unique combination of telco service attributes such as phone, internet, online security, backup, device protection, tech support, streaming TV, and streaming movies.

#### `dim_support_classification`

Purpose:

Stores support ticket categorical attributes.

Primary key:

- `support_classification_key`

Granularity:

- One row per unique combination of ticket type, subject, priority, channel, and status.

### 5.2 Fact Tables

#### `fact_customer_subscription_snapshot`

Source:

- `telco_customer_churn.csv`

Purpose:

Stores churn label, tenure, charges, and subscription state for each telco customer snapshot.

Primary key:

- `subscription_snapshot_key` surrogate key

Foreign keys:

- `customer_key` references `dim_customer.customer_key`
- `contract_key` references `dim_contract.contract_key`
- `service_plan_key` references `dim_service_plan.service_plan_key`

Measures:

- `tenure_months`
- `monthly_charges`
- `total_charges`
- `is_churned`

Granularity:

- One row per customer subscription snapshot.

#### `fact_customer_activity_line`

Source:

- `customer_activity.csv`

Purpose:

Stores transaction-level activity for RFM and behavioral feature engineering.

Primary key:

- `activity_line_key` surrogate key

Foreign keys:

- `customer_key` references `dim_customer.customer_key`, nullable for anonymous transactions
- `product_key` references `dim_product.product_key`
- `invoice_date_key` references `dim_date.date_key`

Degenerate dimensions:

- `invoice_number`

Measures:

- `quantity`
- `unit_price`
- `line_amount = quantity * unit_price`
- `is_return`

Granularity:

- One row per invoice line item.

#### `fact_support_ticket`

Source:

- `support_tickets.csv`

Purpose:

Stores support interactions and service quality signals.

Primary key:

- `ticket_key` surrogate key

Natural key:

- `Ticket ID`

Foreign keys:

- `customer_key` references `dim_customer.customer_key`
- `product_key` references `dim_product.product_key`
- `support_classification_key` references `dim_support_classification.support_classification_key`
- `purchase_date_key` references `dim_date.date_key`
- `first_response_date_key` references `dim_date.date_key`
- `resolution_date_key` references `dim_date.date_key`

Measures:

- `first_response_minutes`
- `resolution_minutes`
- `customer_satisfaction_rating`
- `is_closed`
- `is_open`

Granularity:

- One row per support ticket.

## 6. Final Analytical Table: `churn_features_master`

Purpose:

`churn_features_master` is the final customer-level analytical feature table for churn analytics. It should be built after source cleaning, identity resolution, and fact-table aggregation.

Primary key:

- `customer_key`

Foreign keys:

- `customer_key` references `dim_customer.customer_key`

Granularity:

- One row per customer per feature snapshot date.

Recommended primary key for production:

- Composite key: `customer_key`, `feature_snapshot_date`

Recommended table columns:

| Feature group | Example columns |
|---|---|
| Identity | `customer_key`, `feature_snapshot_date`, `source_systems_present` |
| Churn label | `is_churned` |
| Demographics | `gender`, `senior_citizen_flag`, `partner_flag`, `dependents_flag` |
| Subscription | `tenure_months`, `contract_type`, `internet_service_type`, `phone_service_flag`, `tech_support_flag` |
| Billing | `monthly_charges`, `total_charges`, `payment_method`, `paperless_billing_flag` |
| Activity RFM | `last_activity_date`, `days_since_last_activity`, `invoice_count`, `line_item_count`, `total_quantity`, `gross_revenue`, `net_revenue`, `avg_order_value` |
| Product behavior | `distinct_product_count`, `return_count`, `return_rate`, `country_count`, `primary_country` |
| Support behavior | `ticket_count`, `open_ticket_count`, `closed_ticket_count`, `critical_ticket_count`, `avg_first_response_minutes`, `avg_resolution_minutes`, `avg_satisfaction_rating` |
| Experience flags | `has_open_ticket_flag`, `has_critical_ticket_flag`, `low_satisfaction_flag`, `recent_support_ticket_flag` |
| Audit | `created_at`, `updated_at`, `data_quality_status` |

Important modeling rule:

Features must be generated using only information available on or before `feature_snapshot_date`. This avoids data leakage when the table is later used for modeling.

## 7. Architecture Diagram

```text
                         +----------------------+
                         |   data/raw/*.csv     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   staging tables     |
                         | stg_telco_customer   |
                         | stg_customer_activity|
                         | stg_support_ticket   |
                         +----------+-----------+
                                    |
                                    v
             +----------------------+----------------------+
             |                                             |
             v                                             v
  +----------------------+                    +---------------------------+
  | identity resolution  |                    | standardized dimensions   |
  | dim_customer         |                    | dim_date                  |
  | bridge_customer_id   |                    | dim_product               |
  +----------+-----------+                    | dim_contract              |
             |                                | dim_service_plan          |
             |                                | dim_support_classification|
             |                                +-------------+-------------+
             |                                              |
             +----------------------+-----------------------+
                                    |
                                    v
                         +----------------------+
                         |      fact tables     |
                         | fact_subscription    |
                         | fact_activity_line   |
                         | fact_support_ticket  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | churn_features_master|
                         | one row/customer/    |
                         | snapshot date        |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | BI, analytics, ML    |
                         +----------------------+
```

## 8. Analytics Engineering Best Practices

- Keep raw files immutable in `data/raw`.
- Create staging models that only clean names, cast types, parse dates, and standardize basic values.
- Use surrogate keys for warehouse joins and preserve natural keys for traceability.
- Do not join source systems directly unless the identity relationship is governed and tested.
- Document table grain before defining keys or metrics.
- Separate dimensions from facts.
- Build customer-level features through aggregations from fact tables.
- Use snapshot dates for feature reproducibility and leakage prevention.
- Track null rates, duplicate keys, invalid dates, and orphan foreign keys as data quality checks.
- Keep `churn_features_master` as an analytical output, not a replacement for normalized facts and dimensions.

