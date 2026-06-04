"""Build ML-ready churn features from cleaned customer datasets.

This workflow creates a customer-level feature table for future churn modeling.
It does not train or evaluate any machine learning model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

TARGET_COLUMN = "churn_label"
ID_COLUMN = "unified_customer_id"


def load_cleaned_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load cleaned customer, activity, and support datasets."""
    customers = pd.read_csv(PROCESSED_DIR / "customers_cleaned.csv")
    activity = pd.read_csv(
        PROCESSED_DIR / "customer_activity_cleaned.csv",
        dtype={"invoice": "string", "stock_code": "string"},
    )
    support = pd.read_csv(PROCESSED_DIR / "support_interactions_cleaned.csv")

    activity["invoice_date"] = pd.to_datetime(activity["invoice_date"], errors="coerce")
    support["date_of_purchase"] = pd.to_datetime(support["date_of_purchase"], errors="coerce")
    support["first_response_time"] = pd.to_datetime(support["first_response_time"], errors="coerce")
    support["time_to_resolution"] = pd.to_datetime(support["time_to_resolution"], errors="coerce")

    return customers, activity, support


def most_frequent_value(series: pd.Series):
    """Return the most frequent non-null value in a group."""
    values = series.dropna()
    if values.empty:
        return pd.NA
    return values.mode().iloc[0]


def min_max_scale(series: pd.Series) -> pd.Series:
    """Scale a series to 0-1, protecting against constant inputs."""
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    min_value = series.min()
    max_value = series.max()
    if max_value == min_value:
        return pd.Series(0, index=series.index)
    return (series - min_value) / (max_value - min_value)


def build_activity_features(activity: pd.DataFrame) -> pd.DataFrame:
    """Create customer-level behavior, recency, frequency, and monetary features."""
    valid_activity = activity.loc[activity["invalid_price_flag"].eq(0)].copy()
    observation_end = valid_activity["invoice_date"].max()

    positive_sales = valid_activity.loc[valid_activity["line_amount"] > 0]
    returns = valid_activity.loc[valid_activity["line_amount"] < 0]

    base = (
        valid_activity.groupby(ID_COLUMN)
        .agg(
            activity_line_count=("activity_line_id", "count"),
            invoice_count=("invoice", "nunique"),
            first_activity_date=("invoice_date", "min"),
            last_activity_date=("invoice_date", "max"),
            active_day_count=("invoice_date", lambda value: value.dt.date.nunique()),
            total_quantity=("quantity", "sum"),
            net_activity_revenue=("line_amount", "sum"),
            avg_unit_price=("unit_price", "mean"),
            distinct_product_count=("stock_code", "nunique"),
            return_line_count=("is_return", "sum"),
            countries_count=("country", "nunique"),
            primary_activity_country=("country", most_frequent_value),
            anonymous_activity_line_count=("source_customer_missing_flag", "sum"),
            avg_activity_mapping_confidence=("identity_confidence_score", "mean"),
        )
        .reset_index()
    )

    gross_revenue = (
        positive_sales.groupby(ID_COLUMN)["line_amount"]
        .sum()
        .rename("gross_activity_revenue")
    )
    return_amount = returns.groupby(ID_COLUMN)["line_amount"].sum().abs().rename("return_amount")
    avg_invoice_value = (
        valid_activity.groupby([ID_COLUMN, "invoice"])["line_amount"]
        .sum()
        .groupby(ID_COLUMN)
        .mean()
        .rename("avg_invoice_value")
    )

    base = base.merge(gross_revenue, on=ID_COLUMN, how="left")
    base = base.merge(return_amount, on=ID_COLUMN, how="left")
    base = base.merge(avg_invoice_value, on=ID_COLUMN, how="left")

    base["gross_activity_revenue"] = base["gross_activity_revenue"].fillna(0)
    base["return_amount"] = base["return_amount"].fillna(0)
    base["avg_invoice_value"] = base["avg_invoice_value"].fillna(0)
    base["return_rate"] = base["return_line_count"] / base["activity_line_count"].replace(0, pd.NA)
    base["purchase_frequency_per_active_day"] = base["invoice_count"] / base["active_day_count"].replace(0, pd.NA)
    base["activity_span_days"] = (
        base["last_activity_date"] - base["first_activity_date"]
    ).dt.days.clip(lower=0)
    base["inactivity_days"] = (observation_end - base["last_activity_date"]).dt.days
    base["activity_recency_score"] = 1 - min_max_scale(base["inactivity_days"])
    base["activity_frequency_score"] = min_max_scale(base["invoice_count"])
    base["activity_monetary_score"] = min_max_scale(base["net_activity_revenue"].clip(lower=0))
    base["recency_frequency_metrics"] = (
        0.60 * base["activity_recency_score"] + 0.40 * base["activity_frequency_score"]
    ).round(4)
    base["engagement_score"] = (
        0.45 * base["activity_recency_score"]
        + 0.35 * base["activity_frequency_score"]
        + 0.20 * base["activity_monetary_score"]
    ).round(4)

    return base


def build_support_features(support: pd.DataFrame) -> pd.DataFrame:
    """Create customer-level support friction and dissatisfaction features."""
    working = support.copy()
    working["critical_ticket_flag"] = working["ticket_priority"].eq("critical").astype("int8")
    working["high_priority_ticket_flag"] = working["ticket_priority"].isin(["critical", "high"]).astype("int8")
    working["low_satisfaction_flag"] = working["customer_satisfaction_rating"].le(2).fillna(False).astype("int8")
    working["complaint_flag"] = working["ticket_type"].isin(
        ["technical_issue", "billing_inquiry", "refund_request", "cancellation_request"]
    ).astype("int8")
    working["refund_or_cancel_flag"] = working["ticket_type"].isin(
        ["refund_request", "cancellation_request"]
    ).astype("int8")

    features = (
        working.groupby(ID_COLUMN)
        .agg(
            support_ticket_count=("ticket_id", "count"),
            open_ticket_count=("is_open", "sum"),
            closed_ticket_count=("is_closed", "sum"),
            critical_ticket_count=("critical_ticket_flag", "sum"),
            high_priority_ticket_count=("high_priority_ticket_flag", "sum"),
            low_satisfaction_ticket_count=("low_satisfaction_flag", "sum"),
            complaint_ticket_count=("complaint_flag", "sum"),
            refund_or_cancel_ticket_count=("refund_or_cancel_flag", "sum"),
            unresolved_ticket_count=("resolution_available_flag", lambda value: int((value == 0).sum())),
            avg_satisfaction_rating=("customer_satisfaction_rating", "mean"),
            min_satisfaction_rating=("customer_satisfaction_rating", "min"),
            avg_resolution_hours=("resolution_hours_after_first_response", "mean"),
            max_resolution_hours=("resolution_hours_after_first_response", "max"),
            latest_support_time=("first_response_time", "max"),
            primary_ticket_type=("ticket_type", most_frequent_value),
            primary_ticket_priority=("ticket_priority", most_frequent_value),
            primary_ticket_channel=("ticket_channel", most_frequent_value),
            avg_support_mapping_confidence=("identity_confidence_score", "mean"),
        )
        .reset_index()
    )

    features["open_ticket_rate"] = features["open_ticket_count"] / features["support_ticket_count"].replace(0, pd.NA)
    features["critical_ticket_rate"] = (
        features["critical_ticket_count"] / features["support_ticket_count"].replace(0, pd.NA)
    )
    features["low_satisfaction_rate"] = (
        features["low_satisfaction_ticket_count"] / features["support_ticket_count"].replace(0, pd.NA)
    )
    features["complaint_frequency"] = (
        features["complaint_ticket_count"] / features["support_ticket_count"].replace(0, pd.NA)
    )
    features["support_burden_score"] = (
        0.35 * min_max_scale(features["support_ticket_count"])
        + 0.20 * features["open_ticket_rate"].fillna(0)
        + 0.20 * features["critical_ticket_rate"].fillna(0)
        + 0.15 * features["low_satisfaction_rate"].fillna(0)
        + 0.10 * min_max_scale(features["avg_resolution_hours"])
    ).round(4)

    return features


def build_customer_base(customers: pd.DataFrame) -> pd.DataFrame:
    """Create subscription, payment, and customer value features."""
    base = customers.copy()
    base = base.rename(columns={"is_churned": TARGET_COLUMN})
    base["total_charges_imputed"] = base["total_charges"].fillna(base["monthly_charges"] * base["tenure"])
    base["avg_monthly_spend"] = base["total_charges_imputed"] / base["tenure"].replace(0, pd.NA)
    base["avg_monthly_spend"] = base["avg_monthly_spend"].fillna(base["monthly_charges"])
    base["estimated_customer_lifetime_value"] = base["monthly_charges"] * base["tenure"]
    base["monthly_charge_to_tenure_ratio"] = base["monthly_charges"] / (base["tenure"] + 1)
    base["is_month_to_month_contract"] = base["contract"].eq("month_to_month").astype("int8")
    base["is_electronic_check"] = base["payment_method"].eq("electronic_check").astype("int8")
    base["no_tech_support_flag"] = base["tech_support"].eq("no").astype("int8")
    base["no_online_security_flag"] = base["online_security"].eq("no").astype("int8")
    base["payment_risk_score"] = (
        0.45 * base["is_electronic_check"]
        + 0.35 * base["is_month_to_month_contract"]
        + 0.20 * base["paperless_billing"].eq("yes").astype("int8")
    ).round(4)

    value_rank = base["estimated_customer_lifetime_value"].rank(method="first")
    base["customer_value_segment"] = pd.qcut(
        value_rank,
        q=4,
        labels=["low_value", "emerging_value", "established_value", "high_value"],
    ).astype("string")

    tenure_bins = [-1, 6, 12, 24, 48, 10_000]
    base["tenure_segment"] = pd.cut(
        base["tenure"],
        bins=tenure_bins,
        labels=["0_6_months", "7_12_months", "13_24_months", "25_48_months", "49_plus_months"],
    ).astype("string")

    return base


def build_master_dataframe(
    customers: pd.DataFrame,
    activity: pd.DataFrame,
    support: pd.DataFrame,
) -> pd.DataFrame:
    """Merge all customer-level features into a master dataframe."""
    base = build_customer_base(customers)
    activity_features = build_activity_features(activity)
    support_features = build_support_features(support)

    master = base.merge(activity_features, on=ID_COLUMN, how="left")
    master = master.merge(support_features, on=ID_COLUMN, how="left")

    count_columns = [
        "activity_line_count",
        "invoice_count",
        "active_day_count",
        "total_quantity",
        "distinct_product_count",
        "return_line_count",
        "countries_count",
        "anonymous_activity_line_count",
        "support_ticket_count",
        "open_ticket_count",
        "closed_ticket_count",
        "critical_ticket_count",
        "high_priority_ticket_count",
        "low_satisfaction_ticket_count",
        "complaint_ticket_count",
        "refund_or_cancel_ticket_count",
        "unresolved_ticket_count",
    ]
    for column in count_columns:
        master[column] = master[column].fillna(0)

    numeric_fill_zero = [
        "net_activity_revenue",
        "gross_activity_revenue",
        "return_amount",
        "avg_invoice_value",
        "return_rate",
        "purchase_frequency_per_active_day",
        "activity_span_days",
        "inactivity_days",
        "activity_recency_score",
        "activity_frequency_score",
        "activity_monetary_score",
        "recency_frequency_metrics",
        "engagement_score",
        "open_ticket_rate",
        "critical_ticket_rate",
        "low_satisfaction_rate",
        "complaint_frequency",
        "avg_resolution_hours",
        "max_resolution_hours",
        "support_burden_score",
    ]
    for column in numeric_fill_zero:
        master[column] = master[column].fillna(0)

    master["avg_satisfaction_rating"] = master["avg_satisfaction_rating"].fillna(3)
    master["min_satisfaction_rating"] = master["min_satisfaction_rating"].fillna(3)
    master["has_activity_flag"] = master["activity_line_count"].gt(0).astype("int8")
    master["has_support_flag"] = master["support_ticket_count"].gt(0).astype("int8")
    master["no_activity_flag"] = master["has_activity_flag"].eq(0).astype("int8")
    master["support_to_tenure_ratio"] = master["support_ticket_count"] / (master["tenure"] + 1)
    master["complaints_per_tenure_month"] = master["complaint_ticket_count"] / (master["tenure"] + 1)
    master["monthly_spend_per_invoice"] = master["avg_monthly_spend"] / master["invoice_count"].replace(0, pd.NA)
    master["monthly_spend_per_invoice"] = master["monthly_spend_per_invoice"].fillna(master["avg_monthly_spend"])
    master["customer_health_score"] = (
        0.40 * master["engagement_score"]
        + 0.25 * (1 - master["support_burden_score"].clip(0, 1))
        + 0.20 * (1 - master["payment_risk_score"].clip(0, 1))
        + 0.15 * min_max_scale(master["tenure"])
    ).round(4)

    master["activity_status"] = "no_activity"
    master.loc[master["inactivity_days"].between(0, 30, inclusive="both"), "activity_status"] = "active_0_30_days"
    master.loc[master["inactivity_days"].between(31, 90, inclusive="both"), "activity_status"] = "active_31_90_days"
    master.loc[master["inactivity_days"].gt(90), "activity_status"] = "inactive_90_plus_days"
    master.loc[master["has_activity_flag"].eq(0), "activity_status"] = "no_activity"

    return master


def cap_outliers(df: pd.DataFrame, columns: Iterable[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Cap numeric outliers at the 1st and 99th percentiles."""
    capped = df.copy()
    audit_rows = []

    for column in columns:
        lower = capped[column].quantile(0.01)
        upper = capped[column].quantile(0.99)
        before_lower = int((capped[column] < lower).sum())
        before_upper = int((capped[column] > upper).sum())
        capped[column] = capped[column].clip(lower=lower, upper=upper)
        audit_rows.append(
            {
                "feature": column,
                "lower_cap_p01": lower,
                "upper_cap_p99": upper,
                "values_capped_low": before_lower,
                "values_capped_high": before_upper,
            }
        )

    return capped, pd.DataFrame(audit_rows)


def remove_leakage_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop identifiers, raw labels, dates, free text, and lineage fields not suitable for ML."""
    leakage_columns = [
        "telco_customer_id",
        "churn",
        "customer_source_system",
        "identity_resolution_method",
        "first_activity_date",
        "last_activity_date",
        "activity_observation_end_date",
        "latest_support_time",
    ]
    text_or_lineage_columns = [
        "primary_activity_country",
        "primary_ticket_type",
        "primary_ticket_priority",
        "primary_ticket_channel",
    ]
    drop_columns = [column for column in leakage_columns if column in df.columns]
    return df.drop(columns=drop_columns).copy()


def encode_categorical_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """One-hot encode categorical features and keep a small encoding manifest."""
    categorical_columns = [
        column
        for column in df.select_dtypes(include=["object", "string", "category"]).columns
        if column != ID_COLUMN
    ]
    encoded = pd.get_dummies(df, columns=categorical_columns, dummy_na=True, drop_first=False)
    encoded.columns = [str(column).replace(" ", "_").replace("-", "_").lower() for column in encoded.columns]

    manifest_rows = []
    for column in categorical_columns:
        values = sorted(df[column].dropna().astype(str).unique().tolist())
        manifest_rows.append(
            {
                "source_column": column,
                "encoding": "one_hot",
                "category_count": len(values),
                "categories": ", ".join(values[:30]),
            }
        )
    return encoded, pd.DataFrame(manifest_rows)


def build_correlation_analysis(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Create full feature correlation matrix and target-correlation summary."""
    numeric = df.drop(columns=[ID_COLUMN], errors="ignore").select_dtypes(include=["number"])
    correlation_matrix = numeric.corr()
    target_correlations = (
        correlation_matrix[TARGET_COLUMN]
        .drop(labels=[TARGET_COLUMN], errors="ignore")
        .dropna()
        .sort_values(key=lambda value: value.abs(), ascending=False)
        .reset_index()
    )
    target_correlations.columns = ["feature", "correlation_with_churn_label"]
    return correlation_matrix.reset_index().rename(columns={"index": "feature"}), target_correlations


def build_feature_dictionary() -> pd.DataFrame:
    """Define major engineered features for governance and handoff."""
    rows = [
        ("inactivity_days", "Days since the customer's last mapped activity event.", "Behavioral recency"),
        ("engagement_score", "Weighted recency, frequency, and monetary activity score scaled from 0 to 1.", "Engagement"),
        ("support_burden_score", "Composite score based on ticket volume, open tickets, critical issues, low satisfaction, and resolution time.", "Support friction"),
        ("payment_risk_score", "Transparent score using electronic check, month-to-month contract, and paperless billing indicators.", "Payment and contract risk"),
        ("complaint_frequency", "Share of support tickets that represent complaints, refund, cancellation, billing, or technical issues.", "Complaint behavior"),
        ("avg_monthly_spend", "Historical total charges divided by tenure, with monthly charges used for zero-tenure customers.", "Revenue"),
        ("customer_value_segment", "Quartile segment based on estimated customer lifetime value.", "Value segmentation"),
        ("recency_frequency_metrics", "Weighted score combining activity recency and invoice frequency.", "Behavioral RFM"),
        ("estimated_customer_lifetime_value", "Monthly charges multiplied by tenure.", "CLV indicator"),
        ("customer_health_score", "Composite health score combining engagement, support burden, payment risk, and tenure.", "Customer health"),
        ("support_to_tenure_ratio", "Support tickets normalized by customer tenure.", "Support intensity"),
        ("complaints_per_tenure_month", "Complaint ticket count normalized by customer tenure.", "Complaint intensity"),
        ("return_rate", "Share of activity lines marked as returns.", "Activity quality"),
        ("monthly_spend_per_invoice", "Average monthly spend divided by invoice count, with fallback to average monthly spend.", "Revenue engagement"),
    ]
    return pd.DataFrame(rows, columns=["feature_name", "business_definition", "feature_family"])


def write_markdown_report(
    master: pd.DataFrame,
    final_features: pd.DataFrame,
    feature_dictionary: pd.DataFrame,
    outlier_audit: pd.DataFrame,
    target_correlations: pd.DataFrame,
    encoding_manifest: pd.DataFrame,
) -> None:
    """Write a business and technical feature engineering report."""
    top_corr = target_correlations.head(15)

    markdown = f"""# Churn Feature Engineering Report

## Scope

This workflow creates an ML-ready churn feature dataset from the cleaned
customer, activity, and support interaction tables. It does not train models.

## Analytical Grain

The master dataframe is one row per `unified_customer_id`.

- Pre-encoding master shape: `{master.shape[0]:,}` rows x `{master.shape[1]:,}` columns
- Final ML-ready shape: `{final_features.shape[0]:,}` rows x `{final_features.shape[1]:,}` columns
- Target column: `{TARGET_COLUMN}`

## Major Feature Groups

- Customer subscription and tenure features
- Payment and contract risk features
- Revenue and customer value indicators
- Activity recency, frequency, monetary, return, and engagement features
- Support burden, complaint, dissatisfaction, and resolution features
- Composite health, engagement, support, and payment scores

## Feature Dictionary

{dataframe_to_markdown(feature_dictionary, max_rows=50)}

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

{dataframe_to_markdown(outlier_audit, max_rows=50)}

## Encoding Strategy

Categorical variables are one-hot encoded after leakage columns are removed.
The target remains numeric and is not encoded.

{dataframe_to_markdown(encoding_manifest, max_rows=50)}

## Leakage Controls

The workflow removes raw labels, natural source identifiers, date timestamps,
free-text fields, and lineage-only fields from the final ML-ready dataset.
`unified_customer_id` is retained only as a row identifier, not as a predictive
feature.

## Strongest Target Correlations

These correlations are descriptive diagnostics, not model results.

{dataframe_to_markdown(top_corr, max_rows=15)}

## Outputs

- `data/processed/churn_features_master.csv`
- `data/processed/churn_features_master_pre_encoding.csv`
- `data/processed/churn_feature_dictionary.csv`
- `data/processed/churn_feature_correlation_matrix.csv`
- `data/processed/churn_feature_target_correlations.csv`
- `data/processed/churn_feature_outlier_audit.csv`
- `data/processed/churn_feature_encoding_manifest.csv`
"""
    (PROCESSED_DIR / "churn_feature_engineering_report.md").write_text(markdown, encoding="utf-8")


def dataframe_to_markdown(df: pd.DataFrame, max_rows: int = 20) -> str:
    """Render a dataframe as Markdown without optional dependencies."""
    render_df = df.head(max_rows).copy().fillna("").astype(str)
    headers = list(render_df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in render_df.values.tolist():
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def prepare_final_features(master: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Remove leakage, cap outliers, encode categoricals, and order columns."""
    model_frame = remove_leakage_columns(master)

    outlier_columns = [
        "monthly_charges",
        "total_charges",
        "total_charges_imputed",
        "avg_monthly_spend",
        "estimated_customer_lifetime_value",
        "monthly_charge_to_tenure_ratio",
        "activity_line_count",
        "invoice_count",
        "total_quantity",
        "net_activity_revenue",
        "gross_activity_revenue",
        "return_amount",
        "avg_invoice_value",
        "avg_unit_price",
        "distinct_product_count",
        "support_ticket_count",
        "avg_resolution_hours",
        "max_resolution_hours",
        "support_to_tenure_ratio",
        "complaints_per_tenure_month",
        "monthly_spend_per_invoice",
    ]
    existing_outlier_columns = [column for column in outlier_columns if column in model_frame.columns]
    capped_frame, outlier_audit = cap_outliers(model_frame, existing_outlier_columns)
    encoded_frame, encoding_manifest = encode_categorical_features(capped_frame)

    ordered_columns = [ID_COLUMN, TARGET_COLUMN] + [
        column for column in encoded_frame.columns if column not in [ID_COLUMN, TARGET_COLUMN]
    ]
    encoded_frame = encoded_frame[ordered_columns]

    bool_columns = encoded_frame.select_dtypes(include=["bool"]).columns
    encoded_frame[bool_columns] = encoded_frame[bool_columns].astype("int8")
    encoded_frame = encoded_frame.fillna(0)

    return encoded_frame, outlier_audit, encoding_manifest


def run_workflow() -> None:
    """Run complete feature engineering workflow."""
    customers, activity, support = load_cleaned_datasets()
    master = build_master_dataframe(customers, activity, support)
    final_features, outlier_audit, encoding_manifest = prepare_final_features(master)
    correlation_matrix, target_correlations = build_correlation_analysis(final_features)
    feature_dictionary = build_feature_dictionary()

    master.to_csv(PROCESSED_DIR / "churn_features_master_pre_encoding.csv", index=False)
    final_features.to_csv(PROCESSED_DIR / "churn_features_master.csv", index=False)
    feature_dictionary.to_csv(PROCESSED_DIR / "churn_feature_dictionary.csv", index=False)
    correlation_matrix.to_csv(PROCESSED_DIR / "churn_feature_correlation_matrix.csv", index=False)
    target_correlations.to_csv(PROCESSED_DIR / "churn_feature_target_correlations.csv", index=False)
    outlier_audit.to_csv(PROCESSED_DIR / "churn_feature_outlier_audit.csv", index=False)
    encoding_manifest.to_csv(PROCESSED_DIR / "churn_feature_encoding_manifest.csv", index=False)
    write_markdown_report(
        master,
        final_features,
        feature_dictionary,
        outlier_audit,
        target_correlations,
        encoding_manifest,
    )

    print("Churn feature engineering workflow complete.")
    print(f"Pre-encoding master: {master.shape[0]:,} rows x {master.shape[1]:,} columns")
    print(f"ML-ready features: {final_features.shape[0]:,} rows x {final_features.shape[1]:,} columns")
    print(f"Target column: {TARGET_COLUMN}")


if __name__ == "__main__":
    run_workflow()
