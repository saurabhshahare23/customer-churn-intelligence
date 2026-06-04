"""Clean raw churn source data and build a unified synthetic customer map.

This workflow intentionally stops before feature engineering and machine
learning. It creates governed staging-style outputs that can be joined through
``unified_customer_id`` while preserving source identifiers and match quality.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RAW_FILES = {
    "telco": "telco_customer_churn.csv",
    "activity": "customer_activity.csv",
    "support": "support_tickets.csv",
}


def snake_case(value: str) -> str:
    """Convert a column name or categorical value to lower snake case."""
    value = str(value).strip()
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^0-9A-Za-z]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_").lower()


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with analytics-friendly snake_case column names."""
    clean = df.copy()
    clean.columns = [snake_case(column) for column in clean.columns]
    return clean


def clean_whitespace(series: pd.Series) -> pd.Series:
    """Normalize whitespace while preserving missing values."""
    return (
        series.astype("string")
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )


def clean_category(series: pd.Series) -> pd.Series:
    """Standardize categorical values to lower snake case."""
    return clean_whitespace(series).map(lambda value: snake_case(value) if pd.notna(value) else pd.NA)


def stable_hash_int(value: object) -> int:
    """Create a deterministic integer from any source value."""
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def load_raw_datasets(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Load all raw CSV datasets with pandas."""
    return {name: pd.read_csv(raw_dir / filename) for name, filename in RAW_FILES.items()}


def data_quality_profile(
    df: pd.DataFrame,
    dataset_name: str,
    key_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Create a column-level quality profile for nulls, dtypes, and uniqueness."""
    key_columns = set(key_columns or [])
    rows = []

    for column in df.columns:
        rows.append(
            {
                "dataset": dataset_name,
                "column_name": column,
                "dtype": str(df[column].dtype),
                "row_count": len(df),
                "missing_count": int(df[column].isna().sum()),
                "missing_pct": round(float(df[column].isna().mean()), 6),
                "unique_count": int(df[column].nunique(dropna=True)),
                "is_key_column": column in key_columns,
            }
        )

    return pd.DataFrame(rows)


def build_telco_customers(telco_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean the churn customer source and create canonical customer ids."""
    telco = standardize_columns(telco_raw).drop_duplicates().copy()
    telco = telco.rename(columns={"customer_id": "telco_customer_id"})

    text_columns = telco.select_dtypes(include="object").columns
    for column in text_columns:
        telco[column] = clean_whitespace(telco[column])

    categorical_columns = [
        "gender",
        "partner",
        "dependents",
        "phone_service",
        "multiple_lines",
        "internet_service",
        "online_security",
        "online_backup",
        "device_protection",
        "tech_support",
        "streaming_tv",
        "streaming_movies",
        "contract",
        "paperless_billing",
        "payment_method",
        "churn",
    ]
    for column in categorical_columns:
        telco[column] = clean_category(telco[column])

    telco["senior_citizen"] = pd.to_numeric(telco["senior_citizen"], errors="coerce").astype("Int64")
    telco["tenure"] = pd.to_numeric(telco["tenure"], errors="coerce").astype("Int64")
    telco["monthly_charges"] = pd.to_numeric(telco["monthly_charges"], errors="coerce")
    telco["total_charges"] = pd.to_numeric(telco["total_charges"], errors="coerce")

    telco = telco.sort_values("telco_customer_id").reset_index(drop=True)
    telco["unified_customer_id"] = [f"CUST{idx:07d}" for idx in range(1, len(telco) + 1)]

    customers = telco[
        [
            "unified_customer_id",
            "telco_customer_id",
            "gender",
            "senior_citizen",
            "partner",
            "dependents",
            "tenure",
            "phone_service",
            "multiple_lines",
            "internet_service",
            "online_security",
            "online_backup",
            "device_protection",
            "tech_support",
            "streaming_tv",
            "streaming_movies",
            "contract",
            "paperless_billing",
            "payment_method",
            "monthly_charges",
            "total_charges",
            "churn",
        ]
    ].copy()

    customers["is_churned"] = (customers["churn"] == "yes").astype("int8")
    customers["total_charges_missing_flag"] = customers["total_charges"].isna().astype("int8")
    customers["customer_source_system"] = "telco_customer_churn"
    customers["identity_resolution_method"] = "native_telco_customer_id"
    customers["identity_confidence_score"] = 1.00

    telco_identity = customers[
        ["unified_customer_id", "telco_customer_id", "gender", "senior_citizen"]
    ].copy()
    return customers, telco_identity


def build_activity_map(activity: pd.DataFrame, telco_identity: pd.DataFrame) -> pd.DataFrame:
    """Map activity customer ids to telco customers with a deterministic bridge."""
    unique_activity_ids = (
        activity["source_activity_customer_id"]
        .dropna()
        .astype("Int64")
        .astype(str)
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )
    telco_ids = telco_identity["unified_customer_id"].tolist()

    return pd.DataFrame(
        {
            "source_system": "customer_activity",
            "source_customer_id": unique_activity_ids,
            "unified_customer_id": [
                telco_ids[idx % len(telco_ids)] for idx in range(len(unique_activity_ids))
            ],
            "identity_resolution_method": "synthetic_ranked_activity_customer_id",
            "identity_confidence_score": 0.70,
        }
    )


def clean_customer_activity(
    activity_raw: pd.DataFrame,
    telco_identity: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean activity line data and attach unified customer ids."""
    activity = standardize_columns(activity_raw).drop_duplicates().copy()
    activity = activity.rename(
        columns={
            "customer_id": "source_activity_customer_id",
            "price": "unit_price",
        }
    )

    activity["invoice"] = clean_whitespace(activity["invoice"])
    activity["stock_code"] = clean_whitespace(activity["stock_code"]).str.upper()
    activity["description"] = clean_whitespace(activity["description"])
    activity["country"] = clean_whitespace(activity["country"]).str.title()
    activity["invoice_date"] = pd.to_datetime(activity["invoice_date"], errors="coerce")
    activity["quantity"] = pd.to_numeric(activity["quantity"], errors="coerce").astype("Int64")
    activity["unit_price"] = pd.to_numeric(activity["unit_price"], errors="coerce")
    activity["source_activity_customer_id"] = pd.to_numeric(
        activity["source_activity_customer_id"], errors="coerce"
    ).astype("Int64")

    activity["source_customer_missing_flag"] = activity["source_activity_customer_id"].isna().astype("int8")
    activity["invalid_quantity_flag"] = activity["quantity"].isna().astype("int8")
    activity["invalid_price_flag"] = (activity["unit_price"].isna() | (activity["unit_price"] < 0)).astype("int8")
    activity["is_return"] = (
        (activity["quantity"].fillna(0) < 0) | activity["invoice"].astype("string").str.startswith("C")
    ).astype("int8")
    activity["line_amount"] = activity["quantity"].astype("float") * activity["unit_price"]

    activity_map = build_activity_map(activity, telco_identity)
    activity["source_customer_id_text"] = activity["source_activity_customer_id"].astype("string")
    activity = activity.merge(
        activity_map,
        how="left",
        left_on="source_customer_id_text",
        right_on="source_customer_id",
    )

    telco_ids = telco_identity["unified_customer_id"].tolist()
    missing_mask = activity["unified_customer_id"].isna()
    activity.loc[missing_mask, "unified_customer_id"] = activity.loc[missing_mask, "invoice"].map(
        lambda value: telco_ids[stable_hash_int(value) % len(telco_ids)]
    )
    activity.loc[missing_mask, "identity_resolution_method"] = "synthetic_invoice_hash_for_missing_customer"
    activity.loc[missing_mask, "identity_confidence_score"] = 0.25
    activity.loc[missing_mask, "source_system"] = "customer_activity"

    activity = activity.sort_values(["invoice_date", "invoice", "stock_code"]).reset_index(drop=True)
    activity.insert(0, "activity_line_id", [f"ACT{idx:09d}" for idx in range(1, len(activity) + 1)])

    output_columns = [
        "activity_line_id",
        "unified_customer_id",
        "invoice",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "unit_price",
        "line_amount",
        "country",
        "is_return",
        "source_activity_customer_id",
        "source_customer_missing_flag",
        "invalid_quantity_flag",
        "invalid_price_flag",
        "identity_resolution_method",
        "identity_confidence_score",
    ]
    return activity[output_columns].copy(), activity_map


def build_support_map(support: pd.DataFrame, telco_identity: pd.DataFrame) -> pd.DataFrame:
    """Map support identities to telco customers by demographic segment and hash."""
    support_customers = (
        support[["customer_email", "customer_name", "customer_age", "customer_gender"]]
        .drop_duplicates(subset=["customer_email"])
        .copy()
    )
    support_customers["target_gender"] = support_customers["customer_gender"].map(
        {"male": "male", "female": "female"}
    )
    support_customers["target_senior_citizen"] = (support_customers["customer_age"] >= 65).astype("Int64")

    telco_by_segment = {
        (gender, senior): group["unified_customer_id"].tolist()
        for (gender, senior), group in telco_identity.groupby(["gender", "senior_citizen"])
    }
    all_telco_ids = telco_identity["unified_customer_id"].tolist()

    mapped_ids = []
    methods = []
    scores = []
    for row in support_customers.itertuples(index=False):
        segment = (row.target_gender, row.target_senior_citizen)
        candidates = telco_by_segment.get(segment)
        if candidates:
            mapped_ids.append(candidates[stable_hash_int(row.customer_email) % len(candidates)])
            methods.append("synthetic_email_hash_demographic_segment")
            scores.append(0.65)
        else:
            mapped_ids.append(all_telco_ids[stable_hash_int(row.customer_email) % len(all_telco_ids)])
            methods.append("synthetic_email_hash_global_pool")
            scores.append(0.45)

    return pd.DataFrame(
        {
            "source_system": "support_tickets",
            "source_customer_email": support_customers["customer_email"],
            "source_customer_name": support_customers["customer_name"],
            "unified_customer_id": mapped_ids,
            "identity_resolution_method": methods,
            "identity_confidence_score": scores,
        }
    )


def clean_support_interactions(
    support_raw: pd.DataFrame,
    telco_identity: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean support tickets and attach unified customer ids."""
    support = standardize_columns(support_raw).drop_duplicates().copy()

    text_columns = support.select_dtypes(include="object").columns
    for column in text_columns:
        support[column] = clean_whitespace(support[column])

    support["customer_email"] = support["customer_email"].str.lower()
    category_columns = [
        "customer_gender",
        "product_purchased",
        "ticket_type",
        "ticket_subject",
        "ticket_status",
        "ticket_priority",
        "ticket_channel",
    ]
    for column in category_columns:
        support[column] = clean_category(support[column])

    support["customer_age"] = pd.to_numeric(support["customer_age"], errors="coerce").astype("Int64")
    support["date_of_purchase"] = pd.to_datetime(support["date_of_purchase"], errors="coerce")
    support["first_response_time"] = pd.to_datetime(support["first_response_time"], errors="coerce")
    support["time_to_resolution"] = pd.to_datetime(support["time_to_resolution"], errors="coerce")
    support["customer_satisfaction_rating"] = pd.to_numeric(
        support["customer_satisfaction_rating"], errors="coerce"
    )

    support["invalid_age_flag"] = (
        support["customer_age"].isna() | (support["customer_age"] < 18) | (support["customer_age"] > 100)
    ).astype("int8")
    support["invalid_satisfaction_rating_flag"] = (
        support["customer_satisfaction_rating"].notna()
        & ~support["customer_satisfaction_rating"].between(1, 5)
    ).astype("int8")
    support["resolution_before_response_flag"] = (
        support["time_to_resolution"].notna()
        & support["first_response_time"].notna()
        & (support["time_to_resolution"] < support["first_response_time"])
    ).astype("int8")
    support["is_closed"] = support["ticket_status"].eq("closed").astype("int8")
    support["is_open"] = support["ticket_status"].ne("closed").astype("int8")
    support["response_available_flag"] = support["first_response_time"].notna().astype("int8")
    support["resolution_available_flag"] = support["time_to_resolution"].notna().astype("int8")
    support["resolution_hours_after_first_response"] = (
        (support["time_to_resolution"] - support["first_response_time"]).dt.total_seconds() / 3600
    )

    support_map = build_support_map(support, telco_identity)
    support = support.merge(support_map, how="left", left_on="customer_email", right_on="source_customer_email")
    support = support.sort_values(["first_response_time", "ticket_id"]).reset_index(drop=True)
    support.insert(0, "support_interaction_id", [f"SUP{idx:08d}" for idx in range(1, len(support) + 1)])

    output_columns = [
        "support_interaction_id",
        "unified_customer_id",
        "ticket_id",
        "customer_name",
        "customer_email",
        "customer_age",
        "customer_gender",
        "product_purchased",
        "date_of_purchase",
        "ticket_type",
        "ticket_subject",
        "ticket_status",
        "resolution",
        "ticket_priority",
        "ticket_channel",
        "first_response_time",
        "time_to_resolution",
        "resolution_hours_after_first_response",
        "customer_satisfaction_rating",
        "is_closed",
        "is_open",
        "response_available_flag",
        "resolution_available_flag",
        "invalid_age_flag",
        "invalid_satisfaction_rating_flag",
        "resolution_before_response_flag",
        "identity_resolution_method",
        "identity_confidence_score",
    ]
    return support[output_columns].copy(), support_map


def build_identity_bridge(
    customers: pd.DataFrame,
    activity_cleaned: pd.DataFrame,
    activity_map: pd.DataFrame,
    support_map: pd.DataFrame,
) -> pd.DataFrame:
    """Create an auditable source-to-unified customer bridge."""
    telco_bridge = customers[
        ["unified_customer_id", "telco_customer_id", "identity_resolution_method", "identity_confidence_score"]
    ].copy()
    telco_bridge = telco_bridge.rename(columns={"telco_customer_id": "source_customer_id"})
    telco_bridge["source_system"] = "telco_customer_churn"
    telco_bridge["source_customer_email"] = pd.NA
    telco_bridge["source_customer_name"] = pd.NA

    activity_bridge = activity_map.copy()
    activity_bridge["source_customer_email"] = pd.NA
    activity_bridge["source_customer_name"] = pd.NA

    anonymous_activity_bridge = (
        activity_cleaned.loc[
            activity_cleaned["source_customer_missing_flag"].eq(1),
            [
                "invoice",
                "unified_customer_id",
                "identity_resolution_method",
                "identity_confidence_score",
            ],
        ]
        .drop_duplicates()
        .rename(columns={"invoice": "source_customer_id"})
    )
    anonymous_activity_bridge["source_system"] = "customer_activity"
    anonymous_activity_bridge["source_customer_id"] = (
        "ANON_INVOICE:" + anonymous_activity_bridge["source_customer_id"].astype("string")
    )
    anonymous_activity_bridge["source_customer_email"] = pd.NA
    anonymous_activity_bridge["source_customer_name"] = pd.NA

    support_bridge = support_map.copy()
    support_bridge["source_customer_id"] = pd.NA

    bridge = pd.concat(
        [
            telco_bridge[
                [
                    "source_system",
                    "source_customer_id",
                    "source_customer_email",
                    "source_customer_name",
                    "unified_customer_id",
                    "identity_resolution_method",
                    "identity_confidence_score",
                ]
            ],
            activity_bridge[
                [
                    "source_system",
                    "source_customer_id",
                    "source_customer_email",
                    "source_customer_name",
                    "unified_customer_id",
                    "identity_resolution_method",
                    "identity_confidence_score",
                ]
            ],
            anonymous_activity_bridge[
                [
                    "source_system",
                    "source_customer_id",
                    "source_customer_email",
                    "source_customer_name",
                    "unified_customer_id",
                    "identity_resolution_method",
                    "identity_confidence_score",
                ]
            ],
            support_bridge[
                [
                    "source_system",
                    "source_customer_id",
                    "source_customer_email",
                    "source_customer_name",
                    "unified_customer_id",
                    "identity_resolution_method",
                    "identity_confidence_score",
                ]
            ],
        ],
        ignore_index=True,
    )
    bridge.insert(0, "customer_identity_bridge_id", [f"IDBR{idx:08d}" for idx in range(1, len(bridge) + 1)])
    return bridge


def build_quality_summary(
    raw: dict[str, pd.DataFrame],
    cleaned: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Combine dataset-level and column-level quality checks."""
    dataset_rows = []
    for name, df in raw.items():
        standardized = standardize_columns(df)
        dataset_rows.append(
            {
                "dataset": name,
                "stage": "raw",
                "row_count": len(df),
                "column_count": len(df.columns),
                "duplicate_row_count": int(df.duplicated().sum()),
                "missing_cell_count": int(df.isna().sum().sum()),
            }
        )
        dataset_rows.append(
            {
                "dataset": name,
                "stage": "standardized_raw_columns",
                "row_count": len(standardized),
                "column_count": len(standardized.columns),
                "duplicate_row_count": int(standardized.duplicated().sum()),
                "missing_cell_count": int(standardized.isna().sum().sum()),
            }
        )

    for name, df in cleaned.items():
        dataset_rows.append(
            {
                "dataset": name,
                "stage": "cleaned",
                "row_count": len(df),
                "column_count": len(df.columns),
                "duplicate_row_count": int(df.duplicated().sum()),
                "missing_cell_count": int(df.isna().sum().sum()),
            }
        )

    return pd.DataFrame(dataset_rows)


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    """Render a small DataFrame as a GitHub-style Markdown table without extra deps."""
    render_df = df.fillna("").astype(str)
    headers = list(render_df.columns)
    rows = render_df.values.tolist()

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def write_markdown_summary(processed_dir: Path, quality_summary: pd.DataFrame, bridge: pd.DataFrame) -> None:
    """Write a concise run report for analysts and reviewers."""
    method_summary = (
        bridge.groupby(["source_system", "identity_resolution_method"], dropna=False)
        .size()
        .reset_index(name="identity_count")
    )
    quality_table = dataframe_to_markdown(quality_summary)
    method_table = dataframe_to_markdown(method_summary)

    markdown = f"""# Data Cleaning and Customer Mapping Run Report

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

{quality_table}

## Identity Method Summary

{method_table}

## Cleaned Outputs

- `customers_cleaned.csv`
- `customer_activity_cleaned.csv`
- `support_interactions_cleaned.csv`
- `customer_identity_bridge.csv`
- `data_quality_summary.csv`
- `data_quality_profile.csv`
"""
    (processed_dir / "cleaning_mapping_run_report.md").write_text(markdown, encoding="utf-8")


def run_workflow() -> None:
    """Execute the full data cleaning and customer mapping workflow."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_raw_datasets()

    customers_cleaned, telco_identity = build_telco_customers(raw["telco"])
    activity_cleaned, activity_map = clean_customer_activity(raw["activity"], telco_identity)
    support_cleaned, support_map = clean_support_interactions(raw["support"], telco_identity)
    identity_bridge = build_identity_bridge(customers_cleaned, activity_cleaned, activity_map, support_map)

    cleaned = {
        "customers_cleaned": customers_cleaned,
        "customer_activity_cleaned": activity_cleaned,
        "support_interactions_cleaned": support_cleaned,
        "customer_identity_bridge": identity_bridge,
    }

    quality_profile = pd.concat(
        [
            data_quality_profile(standardize_columns(raw["telco"]), "telco_customer_churn", ["customer_id"]),
            data_quality_profile(standardize_columns(raw["activity"]), "customer_activity", ["invoice", "customer_id"]),
            data_quality_profile(standardize_columns(raw["support"]), "support_tickets", ["ticket_id", "customer_email"]),
        ],
        ignore_index=True,
    )
    quality_summary = build_quality_summary(raw, cleaned)

    customers_cleaned.to_csv(PROCESSED_DIR / "customers_cleaned.csv", index=False)
    activity_cleaned.to_csv(PROCESSED_DIR / "customer_activity_cleaned.csv", index=False)
    support_cleaned.to_csv(PROCESSED_DIR / "support_interactions_cleaned.csv", index=False)
    identity_bridge.to_csv(PROCESSED_DIR / "customer_identity_bridge.csv", index=False)
    quality_summary.to_csv(PROCESSED_DIR / "data_quality_summary.csv", index=False)
    quality_profile.to_csv(PROCESSED_DIR / "data_quality_profile.csv", index=False)
    write_markdown_summary(PROCESSED_DIR, quality_summary, identity_bridge)

    print("Cleaning and customer mapping workflow complete.")
    for name, df in cleaned.items():
        print(f"{name}: {df.shape[0]:,} rows x {df.shape[1]:,} columns")


if __name__ == "__main__":
    run_workflow()
