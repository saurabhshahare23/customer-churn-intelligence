"""Create rule-based retention recommendations from churn scores and features.

The workflow scores all customers with the saved best churn model, applies
transparent business rules, estimates action impact, and writes action-ready
retention outputs. It does not build dashboards.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models" / "trained_models"
MODEL_METRICS_DIR = PROJECT_ROOT / "models" / "model_metrics"
REPORTS_DIR = PROJECT_ROOT / "reports" / "business_reports"

FEATURE_PATH = PROCESSED_DIR / "churn_features_master.csv"
READABLE_FEATURE_PATH = PROCESSED_DIR / "churn_features_master_pre_encoding.csv"
TEST_PREDICTIONS_PATH = MODEL_METRICS_DIR / "best_model_test_predictions.csv"
BEST_MODEL_PATH = MODEL_DIR / "best_churn_model.joblib"
OUTPUT_NAME = "customer_retention_actions.csv"


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


def load_inputs() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, object]]:
    """Load features, readable customer attributes, test predictions, and model package."""
    features = pd.read_csv(FEATURE_PATH)
    readable = pd.read_csv(READABLE_FEATURE_PATH)
    test_predictions = pd.read_csv(TEST_PREDICTIONS_PATH)
    model_package = joblib.load(BEST_MODEL_PATH)
    return features, readable, test_predictions, model_package


def score_all_customers(features: pd.DataFrame, model_package: Dict[str, object]) -> pd.DataFrame:
    """Score every customer with the saved best churn model."""
    model = model_package["model"]
    feature_columns = model_package["feature_columns"]

    X = features[feature_columns].replace([np.inf, -np.inf], np.nan).fillna(0)
    churn_probability = model.predict_proba(X)[:, 1]
    churn_prediction = model.predict(X)

    return pd.DataFrame(
        {
            "unified_customer_id": features["unified_customer_id"],
            "churn_label": features["churn_label"],
            "predicted_churn_probability": churn_probability,
            "predicted_churn_label": churn_prediction,
            "best_model_name": model_package["best_model_name"],
        }
    )


def assign_risk_segment(probability: float) -> str:
    """Convert churn probability into an action-oriented risk segment."""
    if probability >= 0.70:
        return "high risk"
    if probability >= 0.40:
        return "medium risk"
    return "low risk"


def assign_priority(row: pd.Series) -> str:
    """Assign operational priority for retention teams."""
    if row["churn_risk_segment"] == "high risk" and row["customer_value_segment"] == "high_value":
        return "P0 critical"
    if row["churn_risk_segment"] == "high risk":
        return "P1 high"
    if row["churn_risk_segment"] == "medium risk" and row["customer_value_segment"] in [
        "high_value",
        "established_value",
    ]:
        return "P1 high"
    if row["churn_risk_segment"] == "medium risk":
        return "P2 medium"
    return "P3 monitor"


def customer_value_multiplier(value_segment: str) -> float:
    """Estimate impact weight by customer value segment."""
    return {
        "high_value": 1.30,
        "established_value": 1.10,
        "emerging_value": 0.95,
        "low_value": 0.80,
    }.get(value_segment, 1.00)


def choose_recommendation(row: pd.Series) -> Tuple[str, str, str, float, float]:
    """Return primary action, secondary action, reason, expected save rate, and cost."""
    high_value = row["customer_value_segment"] in ["high_value", "established_value"]
    high_risk = row["churn_risk_segment"] == "high risk"
    medium_or_high = row["churn_risk_segment"] in ["medium risk", "high risk"]
    monthly_charge = float(row["monthly_charges"])

    support_friction = (
        row["support_burden_score"] >= 0.45
        or row["open_ticket_count"] > 0
        or row["critical_ticket_count"] > 0
        or row["low_satisfaction_ticket_count"] > 0
        or row["complaint_frequency"] >= 0.50
    )
    inactive = row["no_activity_flag"] == 1 or row["inactivity_days"] > 90 or row["engagement_score"] < 0.35
    payment_risk = row["payment_risk_score"] >= 0.70 or row["is_electronic_check"] == 1
    onboarding_need = row["tenure"] <= 12 or row["customer_health_score"] < 0.40
    price_pressure = row["monthly_charge_to_tenure_ratio"] >= 10 or monthly_charge >= 80

    if support_friction and medium_or_high:
        return (
            "customer support escalation",
            "service recovery follow-up",
            "Support friction is visible through open, critical, complaint, or low satisfaction signals.",
            0.30,
            0.00,
        )
    if high_risk and payment_risk and price_pressure:
        return (
            "discount offer",
            "payment method review",
            "High churn probability combines with payment risk and price pressure.",
            0.24,
            monthly_charge * 0.15,
        )
    if onboarding_need and medium_or_high:
        return (
            "onboarding assistance",
            "product adoption coaching",
            "Early lifecycle or low health customers need help realizing product value.",
            0.22,
            10.00,
        )
    if inactive and medium_or_high:
        return (
            "engagement campaign",
            "personalized usage nudge",
            "Low engagement or long inactivity suggests fading product usage.",
            0.18,
            2.50,
        )
    if payment_risk and medium_or_high:
        return (
            "payment reminders",
            "billing preference optimization",
            "Payment setup resembles higher-risk behavior and should be proactively managed.",
            0.14,
            1.00,
        )
    if high_value and medium_or_high:
        return (
            "loyalty rewards",
            "account manager outreach",
            "Valuable customers should receive recognition before risk becomes urgent.",
            0.16,
            monthly_charge * 0.08,
        )
    return (
        "monitor customer health",
        "next-best-action review",
        "Customer does not currently show a dominant intervention trigger.",
        0.05,
        0.00,
    )


def build_recommendations(
    scores: pd.DataFrame,
    readable: pd.DataFrame,
    test_predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Create customer-level retention recommendations and business impact estimates."""
    rule_columns = [
        "unified_customer_id",
        "telco_customer_id",
        "churn_label",
        "gender",
        "senior_citizen",
        "tenure",
        "contract",
        "payment_method",
        "monthly_charges",
        "total_charges_imputed",
        "avg_monthly_spend",
        "estimated_customer_lifetime_value",
        "monthly_charge_to_tenure_ratio",
        "is_month_to_month_contract",
        "is_electronic_check",
        "payment_risk_score",
        "customer_value_segment",
        "tenure_segment",
        "activity_line_count",
        "invoice_count",
        "inactivity_days",
        "engagement_score",
        "support_ticket_count",
        "open_ticket_count",
        "critical_ticket_count",
        "low_satisfaction_ticket_count",
        "complaint_ticket_count",
        "unresolved_ticket_count",
        "avg_satisfaction_rating",
        "complaint_frequency",
        "support_burden_score",
        "has_activity_flag",
        "has_support_flag",
        "no_activity_flag",
        "customer_health_score",
        "activity_status",
    ]
    available_columns = [column for column in rule_columns if column in readable.columns]
    actions = scores.merge(readable[available_columns], on="unified_customer_id", how="left", suffixes=("", "_feature"))

    if "churn_label_feature" in actions.columns:
        actions = actions.drop(columns=["churn_label_feature"])

    holdout_ids = set(test_predictions["unified_customer_id"])
    actions["prediction_scope"] = actions["unified_customer_id"].map(
        lambda value: "holdout_prediction_output" if value in holdout_ids else "full_model_scoring"
    )
    actions["churn_risk_segment"] = actions["predicted_churn_probability"].map(assign_risk_segment)
    actions["retention_priority"] = actions.apply(assign_priority, axis=1)

    recommendation_rows = actions.apply(choose_recommendation, axis=1, result_type="expand")
    recommendation_rows.columns = [
        "primary_recommendation",
        "secondary_recommendation",
        "recommendation_reason",
        "expected_save_rate",
        "estimated_action_cost",
    ]
    actions = pd.concat([actions, recommendation_rows], axis=1)

    actions["monthly_revenue_at_risk"] = (
        actions["monthly_charges"] * actions["predicted_churn_probability"]
    ).round(2)
    actions["estimated_gross_mrr_saved"] = (
        actions["monthly_revenue_at_risk"]
        * actions["expected_save_rate"]
        * actions["customer_value_segment"].map(customer_value_multiplier).fillna(1.0)
    ).round(2)
    actions["estimated_net_mrr_impact"] = (
        actions["estimated_gross_mrr_saved"] - actions["estimated_action_cost"]
    ).round(2)
    actions["annualized_net_revenue_impact"] = (actions["estimated_net_mrr_impact"] * 12).round(2)
    actions["action_status"] = np.where(actions["churn_label"].eq(1), "winback_review", "active_retention")

    reason_flags = []
    for row in actions.itertuples(index=False):
        flags = []
        if row.inactivity_days > 90 or row.no_activity_flag == 1 or row.engagement_score < 0.35:
            flags.append("low engagement")
        if row.complaint_frequency >= 0.50 or row.support_burden_score >= 0.45 or row.open_ticket_count > 0:
            flags.append("support friction")
        if row.payment_risk_score >= 0.70 or row.is_electronic_check == 1:
            flags.append("payment risk")
        if row.customer_value_segment in ["high_value", "established_value"]:
            flags.append("valuable customer")
        if row.tenure <= 12:
            flags.append("early tenure")
        reason_flags.append(", ".join(flags) if flags else "routine monitoring")
    actions["risk_driver_summary"] = reason_flags

    output_columns = [
        "unified_customer_id",
        "telco_customer_id",
        "action_status",
        "churn_label",
        "predicted_churn_probability",
        "predicted_churn_label",
        "churn_risk_segment",
        "retention_priority",
        "customer_value_segment",
        "monthly_charges",
        "estimated_customer_lifetime_value",
        "monthly_revenue_at_risk",
        "primary_recommendation",
        "secondary_recommendation",
        "recommendation_reason",
        "risk_driver_summary",
        "expected_save_rate",
        "estimated_action_cost",
        "estimated_gross_mrr_saved",
        "estimated_net_mrr_impact",
        "annualized_net_revenue_impact",
        "tenure",
        "tenure_segment",
        "contract",
        "payment_method",
        "payment_risk_score",
        "inactivity_days",
        "activity_status",
        "engagement_score",
        "customer_health_score",
        "support_ticket_count",
        "open_ticket_count",
        "critical_ticket_count",
        "low_satisfaction_ticket_count",
        "complaint_frequency",
        "support_burden_score",
        "avg_satisfaction_rating",
        "prediction_scope",
        "best_model_name",
    ]
    actions = actions[output_columns].sort_values(
        ["retention_priority", "predicted_churn_probability", "estimated_net_mrr_impact"],
        ascending=[True, False, False],
    )
    return actions


def build_summary_tables(actions: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Create management summaries by risk, recommendation, and priority."""
    active = actions.loc[actions["action_status"].eq("active_retention")].copy()

    by_risk = (
        active.groupby("churn_risk_segment")
        .agg(
            customers=("unified_customer_id", "count"),
            avg_churn_probability=("predicted_churn_probability", "mean"),
            monthly_revenue_at_risk=("monthly_revenue_at_risk", "sum"),
            estimated_net_mrr_impact=("estimated_net_mrr_impact", "sum"),
            annualized_net_revenue_impact=("annualized_net_revenue_impact", "sum"),
        )
        .reset_index()
    )

    by_recommendation = (
        active.groupby("primary_recommendation")
        .agg(
            customers=("unified_customer_id", "count"),
            avg_churn_probability=("predicted_churn_probability", "mean"),
            monthly_revenue_at_risk=("monthly_revenue_at_risk", "sum"),
            estimated_net_mrr_impact=("estimated_net_mrr_impact", "sum"),
            annualized_net_revenue_impact=("annualized_net_revenue_impact", "sum"),
        )
        .reset_index()
        .sort_values("estimated_net_mrr_impact", ascending=False)
    )

    by_priority = (
        active.groupby("retention_priority")
        .agg(
            customers=("unified_customer_id", "count"),
            avg_churn_probability=("predicted_churn_probability", "mean"),
            monthly_revenue_at_risk=("monthly_revenue_at_risk", "sum"),
            estimated_net_mrr_impact=("estimated_net_mrr_impact", "sum"),
            annualized_net_revenue_impact=("annualized_net_revenue_impact", "sum"),
        )
        .reset_index()
    )

    return {
        "retention_summary_by_risk.csv": by_risk,
        "retention_summary_by_recommendation.csv": by_recommendation,
        "retention_summary_by_priority.csv": by_priority,
    }


def write_report(actions: pd.DataFrame, summary_tables: Dict[str, pd.DataFrame]) -> None:
    """Write a Markdown retention recommendation playbook."""
    active = actions.loc[actions["action_status"].eq("active_retention")].copy()
    high_risk = active.loc[active["churn_risk_segment"].eq("high risk")]
    priority = active.loc[active["retention_priority"].isin(["P0 critical", "P1 high"])]

    top_actions = actions.loc[actions["action_status"].eq("active_retention")].head(15)

    markdown = f"""# Retention Recommendation Engine Report

## Scope

This workflow converts churn predictions and customer behavior features into
actionable retention recommendations. It does not build dashboards.

## Inputs

- `data/processed/churn_features_master.csv`
- `data/processed/churn_features_master_pre_encoding.csv`
- `models/model_metrics/best_model_test_predictions.csv`
- `models/trained_models/best_churn_model.joblib`

## Recommendation Method

The engine scores all customers with the saved best churn model, assigns risk
segments from churn probability, and applies transparent business rules using:

- Inactivity and engagement score
- Complaint frequency and support burden
- Payment behavior and contract flexibility
- Customer value segment and monthly revenue
- Tenure and customer health

## Risk Segments

- Low risk: churn probability below `0.40`
- Medium risk: churn probability from `0.40` to below `0.70`
- High risk: churn probability `0.70` or higher

## Priority Logic

- `P0 critical`: high-risk, high-value active customers
- `P1 high`: high-risk customers or medium-risk valuable customers
- `P2 medium`: remaining medium-risk customers
- `P3 monitor`: low-risk customers

## Business Impact Summary

- Active customers evaluated: `{len(active):,}`
- High-risk active customers: `{len(high_risk):,}`
- P0/P1 active customers: `{len(priority):,}`
- Active monthly revenue at risk: `{active['monthly_revenue_at_risk'].sum():,.2f}`
- Estimated net monthly retention impact: `{active['estimated_net_mrr_impact'].sum():,.2f}`
- Estimated annualized net retention impact: `{active['annualized_net_revenue_impact'].sum():,.2f}`

## Summary by Recommendation

{dataframe_to_markdown(summary_tables['retention_summary_by_recommendation.csv'], max_rows=20)}

## Summary by Risk Segment

{dataframe_to_markdown(summary_tables['retention_summary_by_risk.csv'], max_rows=10)}

## Top Action Queue

{dataframe_to_markdown(top_actions, max_rows=15)}

## Business Reasoning

- Discount offers are reserved for customers where risk combines with payment
  risk and price pressure, because discounts carry margin cost.
- Onboarding assistance is used for early-tenure or low-health customers where
  the likely issue is value realization rather than price alone.
- Support escalation is prioritized when complaints, open tickets, critical
  tickets, or low satisfaction indicate service friction.
- Payment reminders and billing reviews are targeted to customers with
  electronic check or elevated payment-risk behavior.
- Engagement campaigns are recommended when inactivity or low engagement is the
  clearest churn signal.
- Loyalty rewards are aimed at valuable customers whose risk is meaningful but
  whose issue does not point to a support or billing recovery path.

## Outputs

- `data/processed/customer_retention_actions.csv`
- `reports/business_reports/customer_retention_actions.csv`
- `reports/business_reports/retention_recommendation_report.md`
- `reports/business_reports/retention_summary_by_risk.csv`
- `reports/business_reports/retention_summary_by_recommendation.csv`
- `reports/business_reports/retention_summary_by_priority.csv`
"""
    (REPORTS_DIR / "retention_recommendation_report.md").write_text(markdown, encoding="utf-8")


def run_workflow() -> None:
    """Execute the full retention recommendation workflow."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    features, readable, test_predictions, model_package = load_inputs()
    scores = score_all_customers(features, model_package)
    actions = build_recommendations(scores, readable, test_predictions)
    summary_tables = build_summary_tables(actions)

    actions.to_csv(PROCESSED_DIR / OUTPUT_NAME, index=False)
    actions.to_csv(REPORTS_DIR / OUTPUT_NAME, index=False)

    for file_name, table in summary_tables.items():
        table.to_csv(REPORTS_DIR / file_name, index=False)

    write_report(actions, summary_tables)

    active = actions.loc[actions["action_status"].eq("active_retention")]
    print("Retention recommendation workflow complete.")
    print(f"Customer actions: {actions.shape[0]:,} rows x {actions.shape[1]:,} columns")
    print(f"Active retention customers: {len(active):,}")
    print(f"High-risk active customers: {int(active['churn_risk_segment'].eq('high risk').sum()):,}")


if __name__ == "__main__":
    run_workflow()
