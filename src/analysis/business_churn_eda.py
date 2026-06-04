"""Business-focused exploratory data analysis for churn intelligence.

The workflow consumes cleaned customer, activity, and support datasets, builds a
customer-level analytical dataframe, creates KPI and segment tables, saves
visualizations, and writes a Markdown insights report. It intentionally avoids
machine learning.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
TABLES_DIR = REPORTS_DIR / "business_reports"
FIGURES_DIR = REPORTS_DIR / "figures"
EXPORTS_DIR = REPORTS_DIR / "exports"


def ensure_output_dirs() -> None:
    """Create report output directories."""
    for path in [TABLES_DIR, FIGURES_DIR, EXPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def dataframe_to_markdown(df: pd.DataFrame, max_rows: int = 20) -> str:
    """Render a small dataframe as Markdown without optional dependencies."""
    render_df = df.head(max_rows).copy()
    render_df = render_df.fillna("").astype(str)
    headers = list(render_df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in render_df.values.tolist():
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def load_cleaned_datasets() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load cleaned datasets and parse dates for analysis."""
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
    """Return the most frequent non-null value for a group."""
    values = series.dropna()
    if values.empty:
        return pd.NA
    return values.mode().iloc[0]


def build_activity_features(activity: pd.DataFrame) -> pd.DataFrame:
    """Aggregate invoice-line activity to customer-level engagement features."""
    valid_activity = activity.loc[activity["invalid_price_flag"].eq(0)].copy()
    latest_activity_date = valid_activity["invoice_date"].max()

    positive_sales = valid_activity.loc[valid_activity["line_amount"] > 0]
    positive_revenue = (
        positive_sales.groupby("unified_customer_id")["line_amount"]
        .sum()
        .rename("gross_positive_revenue")
    )
    return_amount = (
        valid_activity.loc[valid_activity["line_amount"] < 0]
        .groupby("unified_customer_id")["line_amount"]
        .sum()
        .abs()
        .rename("return_amount")
    )

    features = (
        valid_activity.groupby("unified_customer_id")
        .agg(
            activity_line_count=("activity_line_id", "count"),
            invoice_count=("invoice", "nunique"),
            first_activity_date=("invoice_date", "min"),
            last_activity_date=("invoice_date", "max"),
            active_day_count=("invoice_date", lambda value: value.dt.date.nunique()),
            total_quantity=("quantity", "sum"),
            net_activity_revenue=("line_amount", "sum"),
            distinct_product_count=("stock_code", "nunique"),
            return_line_count=("is_return", "sum"),
            primary_country=("country", most_frequent_value),
            activity_mapping_confidence=("identity_confidence_score", "mean"),
            anonymous_activity_line_count=("source_customer_missing_flag", "sum"),
        )
        .reset_index()
    )

    features = features.merge(positive_revenue, on="unified_customer_id", how="left")
    features = features.merge(return_amount, on="unified_customer_id", how="left")
    features["gross_positive_revenue"] = features["gross_positive_revenue"].fillna(0)
    features["return_amount"] = features["return_amount"].fillna(0)
    features["avg_order_value"] = features["net_activity_revenue"] / features["invoice_count"].replace(0, pd.NA)
    features["return_rate"] = features["return_line_count"] / features["activity_line_count"].replace(0, pd.NA)
    features["days_since_last_activity"] = (
        latest_activity_date - features["last_activity_date"]
    ).dt.days
    features["activity_observation_end_date"] = latest_activity_date
    return features


def build_support_features(support: pd.DataFrame) -> pd.DataFrame:
    """Aggregate support interactions to customer-level service experience features."""
    low_satisfaction = support["customer_satisfaction_rating"].le(2).fillna(False).astype("int8")
    support = support.copy()
    support["low_satisfaction_flag"] = low_satisfaction
    support["critical_ticket_flag"] = support["ticket_priority"].eq("critical").astype("int8")
    support["refund_or_cancel_flag"] = support["ticket_type"].isin(
        ["refund_request", "cancellation_request"]
    ).astype("int8")

    features = (
        support.groupby("unified_customer_id")
        .agg(
            ticket_count=("ticket_id", "count"),
            open_ticket_count=("is_open", "sum"),
            closed_ticket_count=("is_closed", "sum"),
            critical_ticket_count=("critical_ticket_flag", "sum"),
            low_satisfaction_ticket_count=("low_satisfaction_flag", "sum"),
            refund_or_cancel_ticket_count=("refund_or_cancel_flag", "sum"),
            avg_satisfaction_rating=("customer_satisfaction_rating", "mean"),
            avg_resolution_hours=("resolution_hours_after_first_response", "mean"),
            unresolved_ticket_count=("resolution_available_flag", lambda value: int((value == 0).sum())),
            support_mapping_confidence=("identity_confidence_score", "mean"),
            latest_support_time=("first_response_time", "max"),
            primary_ticket_type=("ticket_type", most_frequent_value),
            primary_ticket_channel=("ticket_channel", most_frequent_value),
        )
        .reset_index()
    )

    features["open_ticket_rate"] = features["open_ticket_count"] / features["ticket_count"].replace(0, pd.NA)
    features["critical_ticket_rate"] = features["critical_ticket_count"] / features["ticket_count"].replace(0, pd.NA)
    features["low_satisfaction_rate"] = (
        features["low_satisfaction_ticket_count"] / features["ticket_count"].replace(0, pd.NA)
    )
    return features


def add_segments(df: pd.DataFrame) -> pd.DataFrame:
    """Add business-friendly customer, value, engagement, and risk segments."""
    analytical = df.copy()

    analytical["tenure_segment"] = pd.cut(
        analytical["tenure"],
        bins=[-1, 6, 12, 24, 48, 10_000],
        labels=["0_6_months", "7_12_months", "13_24_months", "25_48_months", "49_plus_months"],
    ).astype("string")

    analytical["activity_status"] = "no_activity"
    analytical.loc[analytical["days_since_last_activity"].le(30), "activity_status"] = "active_last_30_days"
    analytical.loc[
        analytical["days_since_last_activity"].between(31, 90, inclusive="both"),
        "activity_status",
    ] = "active_31_90_days"
    analytical.loc[analytical["days_since_last_activity"].gt(90), "activity_status"] = "inactive_90_plus_days"

    analytical["support_burden_segment"] = "no_support"
    analytical.loc[analytical["ticket_count"].between(1, 2, inclusive="both"), "support_burden_segment"] = "low_support"
    analytical.loc[analytical["ticket_count"].between(3, 5, inclusive="both"), "support_burden_segment"] = "moderate_support"
    analytical.loc[analytical["ticket_count"].gt(5), "support_burden_segment"] = "high_support"

    revenue_rank = analytical["monthly_charges"].rank(method="first")
    analytical["monthly_revenue_segment"] = pd.qcut(
        revenue_rank,
        q=4,
        labels=["low_revenue", "mid_low_revenue", "mid_high_revenue", "high_revenue"],
    ).astype("string")

    analytical["estimated_clv_indicator"] = analytical["monthly_charges"] * analytical["tenure"]
    clv_rank = analytical["estimated_clv_indicator"].rank(method="first")
    analytical["clv_segment"] = pd.qcut(
        clv_rank,
        q=4,
        labels=["low_clv", "emerging_clv", "established_clv", "high_clv"],
    ).astype("string")

    ticket_threshold = analytical["ticket_count"].quantile(0.75)
    high_charge_threshold = analytical["monthly_charges"].quantile(0.75)

    score = pd.Series(0, index=analytical.index, dtype="float")
    score += analytical["contract"].eq("month_to_month") * 20
    score += analytical["tenure"].le(12) * 20
    score += analytical["tech_support"].eq("no") * 10
    score += analytical["payment_method"].eq("electronic_check") * 10
    score += analytical["activity_status"].isin(["inactive_90_plus_days", "no_activity"]) * 15
    score += analytical["ticket_count"].ge(ticket_threshold) * 10
    score += (
        analytical["open_ticket_count"].gt(0)
        | analytical["critical_ticket_count"].gt(0)
        | analytical["low_satisfaction_ticket_count"].gt(0)
    ) * 10
    score += analytical["monthly_charges"].ge(high_charge_threshold) * 5
    analytical["churn_risk_score"] = score.clip(0, 100).round(0).astype("int64")

    analytical["risk_segment"] = "low_risk"
    analytical.loc[analytical["churn_risk_score"].between(35, 59, inclusive="both"), "risk_segment"] = "medium_risk"
    analytical.loc[analytical["churn_risk_score"].ge(60), "risk_segment"] = "high_risk"

    return analytical


def build_analytical_dataframe(
    customers: pd.DataFrame,
    activity: pd.DataFrame,
    support: pd.DataFrame,
) -> pd.DataFrame:
    """Merge cleaned sources into one customer-level analytical dataframe."""
    activity_features = build_activity_features(activity)
    support_features = build_support_features(support)

    analytical = customers.merge(activity_features, on="unified_customer_id", how="left")
    analytical = analytical.merge(support_features, on="unified_customer_id", how="left")

    count_columns = [
        "activity_line_count",
        "invoice_count",
        "active_day_count",
        "total_quantity",
        "distinct_product_count",
        "return_line_count",
        "anonymous_activity_line_count",
        "ticket_count",
        "open_ticket_count",
        "closed_ticket_count",
        "critical_ticket_count",
        "low_satisfaction_ticket_count",
        "refund_or_cancel_ticket_count",
        "unresolved_ticket_count",
    ]
    amount_columns = [
        "net_activity_revenue",
        "gross_positive_revenue",
        "return_amount",
        "avg_order_value",
        "return_rate",
        "open_ticket_rate",
        "critical_ticket_rate",
        "low_satisfaction_rate",
        "avg_satisfaction_rating",
        "avg_resolution_hours",
    ]
    for column in count_columns:
        analytical[column] = analytical[column].fillna(0)
    for column in amount_columns:
        analytical[column] = analytical[column].fillna(0)

    analytical["has_activity_flag"] = analytical["activity_line_count"].gt(0).astype("int8")
    analytical["has_support_flag"] = analytical["ticket_count"].gt(0).astype("int8")
    analytical["revenue_at_risk"] = analytical["monthly_charges"] * analytical["is_churned"]
    analytical["observed_customer_value"] = analytical["total_charges"].fillna(
        analytical["monthly_charges"] * analytical["tenure"]
    )

    return add_segments(analytical)


def percent(value: float) -> float:
    """Convert a decimal ratio to rounded percentage."""
    return round(float(value) * 100, 2)


def build_kpi_table(df: pd.DataFrame) -> pd.DataFrame:
    """Create business-oriented KPI table."""
    total_customers = len(df)
    churned_customers = int(df["is_churned"].sum())
    retained_customers = total_customers - churned_customers
    active_customers = int(df["has_activity_flag"].sum())
    supported_customers = int(df["has_support_flag"].sum())

    kpis = [
        ("total_customers", total_customers, "Count of cleaned customer records."),
        ("churned_customers", churned_customers, "Customers with observed churn label."),
        ("retained_customers", retained_customers, "Customers that have not churned."),
        ("churn_rate_pct", percent(df["is_churned"].mean()), "Observed churned customers / total customers."),
        ("retention_rate_pct", percent(1 - df["is_churned"].mean()), "Observed retained customers / total customers."),
        ("arpu_monthly_charges", round(df["monthly_charges"].mean(), 2), "Average monthly charge per customer."),
        ("avg_total_charges", round(df["total_charges"].mean(), 2), "Average historical charges per customer."),
        ("avg_estimated_clv_indicator", round(df["estimated_clv_indicator"].mean(), 2), "Monthly charges multiplied by tenure."),
        ("monthly_revenue_at_risk", round(df["revenue_at_risk"].sum(), 2), "Monthly recurring revenue tied to churned customers."),
        ("active_customer_rate_pct", percent(active_customers / total_customers), "Customers with mapped activity records."),
        ("avg_invoice_count", round(df["invoice_count"].mean(), 2), "Average distinct invoices per customer."),
        ("avg_net_activity_revenue", round(df["net_activity_revenue"].mean(), 2), "Average mapped activity revenue per customer."),
        ("support_customer_rate_pct", percent(supported_customers / total_customers), "Customers with support interactions."),
        ("avg_tickets_per_customer", round(df["ticket_count"].mean(), 2), "Average support tickets per customer."),
        ("open_ticket_rate_pct", percent(df["open_ticket_count"].sum() / df["ticket_count"].sum()), "Open tickets / all tickets."),
        ("avg_satisfaction_rating", round(df.loc[df["avg_satisfaction_rating"] > 0, "avg_satisfaction_rating"].mean(), 2), "Average satisfaction among rated customers."),
    ]
    return pd.DataFrame(kpis, columns=["kpi", "value", "business_definition"])


def segment_summary(df: pd.DataFrame, group_columns: List[str], output_name: str) -> pd.DataFrame:
    """Create a reusable churn and value summary by segment."""
    grouped = (
        df.groupby(group_columns, dropna=False)
        .agg(
            customers=("unified_customer_id", "count"),
            churn_rate=("is_churned", "mean"),
            avg_monthly_charges=("monthly_charges", "mean"),
            avg_tenure=("tenure", "mean"),
            avg_invoice_count=("invoice_count", "mean"),
            avg_ticket_count=("ticket_count", "mean"),
            avg_risk_score=("churn_risk_score", "mean"),
        )
        .reset_index()
    )
    grouped["churn_rate_pct"] = (grouped["churn_rate"] * 100).round(2)
    grouped = grouped.drop(columns=["churn_rate"])
    grouped = grouped.sort_values(["churn_rate_pct", "customers"], ascending=[False, False])
    grouped.to_csv(TABLES_DIR / output_name, index=False)
    return grouped


def create_summary_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Create high-risk, low-engagement, high-value, and segment summary tables."""
    current_customers = df.loc[df["is_churned"].eq(0)].copy()

    high_risk = (
        current_customers.sort_values(
            ["churn_risk_score", "monthly_charges", "ticket_count", "days_since_last_activity"],
            ascending=[False, False, False, False],
        )
        [
            [
                "unified_customer_id",
                "contract",
                "tenure",
                "monthly_charges",
                "activity_status",
                "ticket_count",
                "open_ticket_count",
                "avg_satisfaction_rating",
                "churn_risk_score",
                "risk_segment",
            ]
        ]
        .head(100)
    )

    low_engagement = (
        current_customers.sort_values(
            ["has_activity_flag", "days_since_last_activity", "invoice_count", "monthly_charges"],
            ascending=[True, False, True, False],
        )
        [
            [
                "unified_customer_id",
                "contract",
                "tenure",
                "monthly_charges",
                "activity_status",
                "days_since_last_activity",
                "invoice_count",
                "net_activity_revenue",
                "churn_risk_score",
            ]
        ]
        .head(100)
    )

    high_value = (
        current_customers.sort_values(
            ["estimated_clv_indicator", "monthly_charges", "observed_customer_value"],
            ascending=[False, False, False],
        )
        [
            [
                "unified_customer_id",
                "contract",
                "tenure",
                "monthly_charges",
                "total_charges",
                "estimated_clv_indicator",
                "invoice_count",
                "ticket_count",
                "churn_risk_score",
                "risk_segment",
            ]
        ]
        .head(100)
    )

    tables = {
        "high_risk_customers": high_risk,
        "low_engagement_customers": low_engagement,
        "high_value_customers": high_value,
        "churn_by_contract": segment_summary(df, ["contract"], "churn_by_contract.csv"),
        "churn_by_tenure_segment": segment_summary(df, ["tenure_segment"], "churn_by_tenure_segment.csv"),
        "churn_by_activity_status": segment_summary(df, ["activity_status"], "churn_by_activity_status.csv"),
        "churn_by_support_burden": segment_summary(df, ["support_burden_segment"], "churn_by_support_burden.csv"),
        "churn_by_revenue_segment": segment_summary(df, ["monthly_revenue_segment"], "churn_by_revenue_segment.csv"),
    }

    for name in ["high_risk_customers", "low_engagement_customers", "high_value_customers"]:
        tables[name].to_csv(TABLES_DIR / f"{name}.csv", index=False)

    return tables


def save_barplot(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    xlabel: str,
    ylabel: str,
    file_name: str,
    rotation: int = 20,
) -> None:
    """Save a labeled business bar chart."""
    plt.figure(figsize=(10, 5.5))
    sns.barplot(data=df, x=x, y=y, color="#3A7D7C")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=rotation, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / file_name, dpi=160)
    plt.close()


def create_visualizations(df: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> List[str]:
    """Create matplotlib and seaborn visualizations for churn storytelling."""
    sns.set_theme(style="whitegrid", context="talk")
    figure_paths = []

    chart_specs = [
        ("churn_by_contract", "contract", "churn_rate_pct", "Churn Rate by Contract Type", "Contract", "Churn rate (%)", "churn_rate_by_contract.png"),
        ("churn_by_tenure_segment", "tenure_segment", "churn_rate_pct", "Churn Rate by Tenure Segment", "Tenure segment", "Churn rate (%)", "churn_rate_by_tenure_segment.png"),
        ("churn_by_activity_status", "activity_status", "churn_rate_pct", "Churn Rate by Engagement Status", "Engagement status", "Churn rate (%)", "churn_rate_by_activity_status.png"),
        ("churn_by_support_burden", "support_burden_segment", "churn_rate_pct", "Churn Rate by Support Burden", "Support burden", "Churn rate (%)", "churn_rate_by_support_burden.png"),
        ("churn_by_revenue_segment", "monthly_revenue_segment", "churn_rate_pct", "Churn Rate by Revenue Segment", "Revenue segment", "Churn rate (%)", "churn_rate_by_revenue_segment.png"),
    ]

    for table_name, x, y, title, xlabel, ylabel, file_name in chart_specs:
        save_barplot(tables[table_name], x, y, title, xlabel, ylabel, file_name)
        figure_paths.append(str(FIGURES_DIR / file_name))

    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x="is_churned", y="monthly_charges", palette=["#4C78A8", "#D65F5F"])
    plt.title("Monthly Charges Distribution by Churn Outcome")
    plt.xlabel("Churned customer flag")
    plt.ylabel("Monthly charges")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "monthly_charges_by_churn.png", dpi=160)
    plt.close()
    figure_paths.append(str(FIGURES_DIR / "monthly_charges_by_churn.png"))

    plt.figure(figsize=(10, 6))
    sns.histplot(data=df, x="tenure", hue="churn", bins=30, multiple="stack", palette=["#4C78A8", "#D65F5F"])
    plt.title("Customer Tenure Distribution by Churn")
    plt.xlabel("Tenure in months")
    plt.ylabel("Customer count")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "tenure_distribution_by_churn.png", dpi=160)
    plt.close()
    figure_paths.append(str(FIGURES_DIR / "tenure_distribution_by_churn.png"))

    numeric_columns = [
        "is_churned",
        "tenure",
        "monthly_charges",
        "estimated_clv_indicator",
        "invoice_count",
        "days_since_last_activity",
        "ticket_count",
        "open_ticket_count",
        "critical_ticket_count",
        "avg_satisfaction_rating",
        "churn_risk_score",
    ]
    corr = df[numeric_columns].corr()
    plt.figure(figsize=(11, 8))
    sns.heatmap(corr, cmap="vlag", center=0, annot=False, linewidths=0.5)
    plt.title("Customer Churn Driver Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "churn_driver_correlation_heatmap.png", dpi=160)
    plt.close()
    figure_paths.append(str(FIGURES_DIR / "churn_driver_correlation_heatmap.png"))

    plt.figure(figsize=(10, 6))
    sns.scatterplot(
        data=df.sample(min(len(df), 2500), random_state=42),
        x="monthly_charges",
        y="tenure",
        hue="churn",
        size="ticket_count",
        sizes=(20, 180),
        alpha=0.65,
        palette=["#4C78A8", "#D65F5F"],
    )
    plt.title("Customer Value, Tenure, and Support Burden")
    plt.xlabel("Monthly charges")
    plt.ylabel("Tenure in months")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "value_tenure_support_scatter.png", dpi=160)
    plt.close()
    figure_paths.append(str(FIGURES_DIR / "value_tenure_support_scatter.png"))

    return figure_paths


def top_segment_insight(table: pd.DataFrame, segment_column: str) -> str:
    """Return a compact business sentence for the highest-churn segment."""
    top = table.sort_values(["churn_rate_pct", "customers"], ascending=[False, False]).iloc[0]
    return (
        f"`{top[segment_column]}` has the highest observed churn rate at "
        f"{top['churn_rate_pct']}% across {int(top['customers'])} customers."
    )


def write_business_report(
    df: pd.DataFrame,
    kpis: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    figure_paths: List[str],
) -> None:
    """Write a Markdown EDA report with business interpretation."""
    churn_rate = float(kpis.loc[kpis["kpi"].eq("churn_rate_pct"), "value"].iloc[0])
    retention_rate = float(kpis.loc[kpis["kpi"].eq("retention_rate_pct"), "value"].iloc[0])
    arpu = float(kpis.loc[kpis["kpi"].eq("arpu_monthly_charges"), "value"].iloc[0])
    revenue_at_risk = float(kpis.loc[kpis["kpi"].eq("monthly_revenue_at_risk"), "value"].iloc[0])

    current_customers = df.loc[df["is_churned"].eq(0)]
    high_risk_current = int(current_customers["risk_segment"].eq("high_risk").sum())
    high_value_at_risk = int(
        (
            current_customers["risk_segment"].eq("high_risk")
            & current_customers["clv_segment"].eq("high_clv")
        ).sum()
    )

    report = f"""# Business Churn EDA Report

## Executive Summary

This exploratory workflow merges cleaned customer, activity, and support data
into a customer-level analytical dataframe. It focuses on business
understanding: churn behavior, customer segments, revenue exposure, engagement
signals, and support dissatisfaction. No machine learning models are trained.

The observed churn rate is **{churn_rate}%**, with a retention rate of
**{retention_rate}%**. Average monthly revenue per user is **{arpu}**, and
monthly revenue already associated with churned customers is **{revenue_at_risk}**.

## Unified Analytical Dataset

The unified dataframe is written to `reports/exports/customer_churn_analytical_dataframe.csv`.
It uses `unified_customer_id` as the customer grain and includes:

- Customer subscription and churn attributes
- Activity recency, frequency, monetary value, returns, and product breadth
- Support ticket volume, open ticket counts, priority mix, satisfaction, and resolution timing
- Business segments for tenure, engagement, revenue, support burden, CLV, and risk

## KPI Scorecard

{dataframe_to_markdown(kpis, max_rows=30)}

## Churn Trends

- {top_segment_insight(tables["churn_by_contract"], "contract")}
- {top_segment_insight(tables["churn_by_tenure_segment"], "tenure_segment")}
- {top_segment_insight(tables["churn_by_revenue_segment"], "monthly_revenue_segment")}

Business interpretation: churn should be read as a behavioral and commercial
pattern, not only as a target label. Contract structure, tenure maturity, and
revenue intensity are especially useful lenses for retention planning.

## Engagement Patterns

{dataframe_to_markdown(tables["churn_by_activity_status"], max_rows=10)}

Customers with weak or stale activity deserve dedicated lifecycle review.
Inactivity is especially important when paired with month-to-month contracts,
high monthly charges, or unresolved support issues.

## Support Dissatisfaction Signals

{dataframe_to_markdown(tables["churn_by_support_burden"], max_rows=10)}

Support burden is treated as an experience signal. High ticket volume, open
tickets, critical priorities, refund or cancellation requests, and low
satisfaction ratings can all indicate friction that may precede churn.

## High-Risk Customers

The high-risk list focuses on currently retained customers with elevated
non-model risk scores. There are **{high_risk_current}** retained customers in
the high-risk segment, including **{high_value_at_risk}** high-CLV customers.

{dataframe_to_markdown(tables["high_risk_customers"].head(10), max_rows=10)}

## Low-Engagement Customers

{dataframe_to_markdown(tables["low_engagement_customers"].head(10), max_rows=10)}

## High-Value Customers

{dataframe_to_markdown(tables["high_value_customers"].head(10), max_rows=10)}

## Key Business Insights

1. Contract and tenure are central churn lenses. Customers on flexible contracts
   and early-tenure customers should be prioritized for onboarding, plan-fit
   reviews, and retention offers.
2. Revenue exposure is not evenly distributed. High monthly charges and high
   estimated CLV should be paired with risk indicators to prioritize
   intervention value.
3. Inactivity is a practical leading indicator. Customers with stale or missing
   activity can be routed into re-engagement campaigns before churn is observed.
4. Support friction adds operational context to churn. Open, critical, refund,
   cancellation, and low-satisfaction tickets should feed customer health
   monitoring.
5. The synthetic identity bridge enables cross-source analysis, but match
   confidence should be considered when making customer-level decisions.

## Visualizations

The workflow saves matplotlib/seaborn charts to `reports/figures/`:

{chr(10).join("- `" + Path(path).name + "`" for path in figure_paths)}
"""
    (TABLES_DIR / "business_churn_eda_report.md").write_text(report, encoding="utf-8")


def run_workflow() -> None:
    """Execute the full business EDA workflow."""
    ensure_output_dirs()
    customers, activity, support = load_cleaned_datasets()

    analytical = build_analytical_dataframe(customers, activity, support)
    analytical.to_csv(EXPORTS_DIR / "customer_churn_analytical_dataframe.csv", index=False)

    kpis = build_kpi_table(analytical)
    kpis.to_csv(TABLES_DIR / "business_kpi_scorecard.csv", index=False)

    tables = create_summary_tables(analytical)
    figure_paths = create_visualizations(analytical, tables)
    write_business_report(analytical, kpis, tables, figure_paths)

    print("Business churn EDA workflow complete.")
    print(f"Analytical dataframe: {analytical.shape[0]:,} rows x {analytical.shape[1]:,} columns")
    print(f"KPI table: {len(kpis):,} metrics")
    print(f"Visualizations: {len(figure_paths):,} charts")


if __name__ == "__main__":
    run_workflow()
