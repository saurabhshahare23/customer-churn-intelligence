# Data Cleaning and Customer Mapping Workflow

## Purpose

This workflow prepares the raw churn, customer activity, and support ticket
datasets for analytics by standardizing schemas, cleaning values, validating
quality issues, and creating a unified synthetic customer key.

Machine learning is intentionally out of scope. The output is a clean,
join-ready analytical foundation.

## Inputs

Raw files are treated as immutable source data:

- `data/raw/telco_customer_churn.csv`
- `data/raw/customer_activity.csv`
- `data/raw/support_tickets.csv`

## Outputs

The workflow writes these files to `data/processed/`:

- `customers_cleaned.csv`
- `customer_activity_cleaned.csv`
- `support_interactions_cleaned.csv`
- `customer_identity_bridge.csv`
- `data_quality_summary.csv`
- `data_quality_profile.csv`
- `cleaning_mapping_run_report.md`

## Processing Steps

### 1. Load Datasets

All datasets are loaded with pandas in `src/preprocessing/clean_customer_mapping.py`.
The loader keeps file paths centralized so the pipeline can be scheduled or
wrapped by orchestration tools later.

### 2. Standardize Column Names

Every source column is converted to lower snake case. This avoids fragile
case-sensitive joins and makes the cleaned outputs friendlier for SQL,
dbt-style modeling, notebooks, and BI tools.

### 3. Run Data Quality Checks

The workflow profiles:

- Missing values
- Duplicate rows
- Source dtypes
- Unique counts
- Key candidate columns
- Invalid numeric and date values after casting

Important quality conditions are retained as flags. The pipeline does not hide
data issues by dropping large groups of records silently.

### 4. Clean Text and Categorical Fields

Text fields are trimmed and repeated whitespace is collapsed. Categorical fields
are standardized to lower snake case values, for example `Month-to-month`
becomes `month_to_month`.

### 5. Convert Dates and Numeric Fields

Date fields are parsed with `pd.to_datetime(..., errors="coerce")`. Invalid
dates become nulls and remain visible in the quality profile.

Numeric fields are parsed with `pd.to_numeric(..., errors="coerce")`. Examples
include charges, unit price, quantity, age, and satisfaction rating.

### 6. Create Unified Customer Mapping

The three sources do not share a real customer key. The workflow therefore uses
a deterministic synthetic identity bridge:

- Telco records use the native `telco_customer_id` and receive confidence `1.00`.
- Known activity customer ids are mapped into the Telco customer pool by stable
  sorted rank and receive confidence `0.70`.
- Activity rows with missing source customer ids are assigned by invoice hash and
  receive confidence `0.25`.
- Support customers are mapped by email hash within a gender and senior-citizen
  segment where possible and receive confidence `0.65`.
- Support customers that cannot use a demographic segment fall back to a global
  email hash and receive confidence `0.45`.

All rules are deterministic, meaning the same raw data produces the same
customer mappings on every run.

## Analytics Engineering Notes

- Raw data remains immutable in `data/raw`.
- Cleaned files include the canonical `unified_customer_id`.
- Source identifiers are preserved for lineage and troubleshooting.
- Match confidence and resolution method are stored next to mapped records.
- Invalid values are flagged, not erased.
- The workflow creates an identity bridge instead of hard-coding joins in each
  downstream analysis.
- The cleaned tables are staging-grade outputs; customer-level feature tables
  should be built later from these tables with clear snapshot dates to avoid
  leakage.

## Run Command

From the project root:

```bash
python src/preprocessing/clean_customer_mapping.py
```
