"""Business impact simulator for churn retention campaigns.

The simulator combines churn predictions, retention recommendations, and
customer value features to estimate revenue at risk, recovery potential, ROI,
and segment-level financial impact. It does not build dashboards.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Tuple

import matplotlib
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")

import matplotlib.pyplot as plt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_METRICS_DIR = PROJECT_ROOT / "models" / "model_metrics"
REPORTS_DIR = PROJECT_ROOT / "reports" / "business_reports"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"

PREDICTION_OUTPUT_PATH = MODEL_METRICS_DIR / "best_model_test_predictions.csv"
RETENTION_ACTIONS_PATH = REPORTS_DIR / "customer_retention_actions.csv"
FEATURES_PATH = PROCESSED_DIR / "churn_features_master.csv"

SCENARIOS = [
    ("Scenario A", "Retain top 5% high-risk customers", 0.05),
    ("Scenario B", "Retain top 10% high-risk customers", 0.10),
    ("Scenario C", "Retain top 20% high-risk customers", 0.20),
]


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


def load_inputs() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load churn prediction outputs, retention actions, and customer features."""
    predictions = pd.read_csv(PREDICTION_OUTPUT_PATH)
    actions = pd.read_csv(RETENTION_ACTIONS_PATH)
    features = pd.read_csv(FEATURES_PATH)
    return predictions, actions, features


def enrich_financial_metrics(actions: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Add revenue loss, recovery, and CLV impact metrics to action records."""
    value_columns = [
        "unified_customer_id",
        "total_charges_imputed",
        "avg_monthly_spend",
        "estimated_customer_lifetime_value",
        "customer_health_score",
    ]
    available = [column for column in value_columns if column in features.columns]
    enriched = actions.merge(features[available], on="unified_customer_id", how="left", suffixes=("", "_feature"))

    if "estimated_customer_lifetime_value_feature" in enriched.columns:
        enriched["estimated_customer_lifetime_value"] = enriched["estimated_customer_lifetime_value"].fillna(
            enriched["estimated_customer_lifetime_value_feature"]
        )

    enriched["expected_monthly_revenue_loss"] = enriched["monthly_revenue_at_risk"].round(2)
    enriched["expected_annual_revenue_loss"] = (enriched["expected_monthly_revenue_loss"] * 12).round(2)
    enriched["expected_clv_at_risk"] = (
        enriched["estimated_customer_lifetime_value"] * enriched["predicted_churn_probability"]
    ).round(2)
    enriched["revenue_recovery_potential"] = enriched["estimated_gross_mrr_saved"].round(2)
    enriched["net_recovery_potential"] = enriched["estimated_net_mrr_impact"].round(2)
    enriched["annualized_recovery_potential"] = (enriched["net_recovery_potential"] * 12).round(2)
    return enriched


def build_kpi_summary(enriched: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    """Create executive KPI summary for revenue exposure and recovery potential."""
    active = enriched.loc[enriched["action_status"].eq("active_retention")]
    high_risk = active.loc[active["churn_risk_segment"].eq("high risk")]

    rows = [
        ("customers_scored", len(enriched), "All customers scored by the saved churn model."),
        ("active_customers_evaluated", len(active), "Customers eligible for retention actions."),
        ("holdout_prediction_rows_loaded", len(predictions), "Rows loaded from model holdout prediction output."),
        ("active_high_risk_customers", len(high_risk), "Active customers with churn probability >= 0.70."),
        ("monthly_revenue_at_risk", round(active["expected_monthly_revenue_loss"].sum(), 2), "Probability-weighted monthly revenue exposure."),
        ("annual_revenue_at_risk", round(active["expected_annual_revenue_loss"].sum(), 2), "Probability-weighted annual revenue exposure."),
        ("customer_lifetime_value_at_risk", round(active["expected_clv_at_risk"].sum(), 2), "Probability-weighted CLV exposure."),
        ("monthly_recovery_potential", round(active["revenue_recovery_potential"].sum(), 2), "Estimated gross monthly revenue recoverable from recommended actions."),
        ("net_monthly_recovery_potential", round(active["net_recovery_potential"].sum(), 2), "Gross recovery less estimated action cost."),
        ("annualized_net_recovery_potential", round(active["annualized_recovery_potential"].sum(), 2), "Annualized net recovery potential."),
    ]
    return pd.DataFrame(rows, columns=["kpi", "value", "business_definition"])


def simulate_scenarios(enriched: pd.DataFrame) -> pd.DataFrame:
    """Simulate retaining top high-risk active customers by churn probability and impact."""
    active_high_risk = (
        enriched.loc[
            enriched["action_status"].eq("active_retention")
            & enriched["churn_risk_segment"].eq("high risk")
        ]
        .sort_values(
            ["predicted_churn_probability", "monthly_revenue_at_risk", "estimated_customer_lifetime_value"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )

    rows = []
    pool_size = len(active_high_risk)
    for scenario_name, description, fraction in SCENARIOS:
        selected_count = max(1, math.ceil(pool_size * fraction)) if pool_size else 0
        selected = active_high_risk.head(selected_count)

        expected_customers_saved = selected["expected_save_rate"].sum()
        campaign_cost = selected["estimated_action_cost"].sum()
        gross_monthly_revenue_saved = selected["estimated_gross_mrr_saved"].sum()
        net_monthly_revenue_saved = selected["estimated_net_mrr_impact"].sum()
        annualized_net_revenue_saved = selected["annualized_net_revenue_impact"].sum()
        clv_protected = (selected["expected_clv_at_risk"] * selected["expected_save_rate"]).sum()
        roi = net_monthly_revenue_saved / campaign_cost if campaign_cost > 0 else None

        rows.append(
            {
                "scenario": scenario_name,
                "scenario_description": description,
                "target_high_risk_pct": fraction,
                "high_risk_pool_customers": pool_size,
                "customers_targeted": selected_count,
                "expected_customers_saved": round(expected_customers_saved, 2),
                "retention_effectiveness_pct": round(expected_customers_saved / selected_count * 100, 2) if selected_count else 0,
                "monthly_revenue_at_risk_targeted": round(selected["monthly_revenue_at_risk"].sum(), 2),
                "gross_monthly_revenue_saved": round(gross_monthly_revenue_saved, 2),
                "campaign_cost": round(campaign_cost, 2),
                "net_monthly_revenue_saved": round(net_monthly_revenue_saved, 2),
                "annualized_net_revenue_saved": round(annualized_net_revenue_saved, 2),
                "customer_lifetime_value_protected": round(clv_protected, 2),
                "estimated_roi_pct": round(roi * 100, 2) if roi is not None else None,
            }
        )
    return pd.DataFrame(rows)


def build_segment_summaries(enriched: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Build executive summary tables for segment-level financial impact."""
    active = enriched.loc[enriched["action_status"].eq("active_retention")].copy()

    by_value = (
        active.groupby("customer_value_segment")
        .agg(
            customers=("unified_customer_id", "count"),
            avg_churn_probability=("predicted_churn_probability", "mean"),
            monthly_revenue_at_risk=("expected_monthly_revenue_loss", "sum"),
            expected_clv_at_risk=("expected_clv_at_risk", "sum"),
            net_monthly_recovery_potential=("net_recovery_potential", "sum"),
            annualized_recovery_potential=("annualized_recovery_potential", "sum"),
        )
        .reset_index()
        .sort_values("monthly_revenue_at_risk", ascending=False)
    )

    by_risk = (
        active.groupby("churn_risk_segment")
        .agg(
            customers=("unified_customer_id", "count"),
            avg_churn_probability=("predicted_churn_probability", "mean"),
            monthly_revenue_at_risk=("expected_monthly_revenue_loss", "sum"),
            expected_clv_at_risk=("expected_clv_at_risk", "sum"),
            net_monthly_recovery_potential=("net_recovery_potential", "sum"),
            annualized_recovery_potential=("annualized_recovery_potential", "sum"),
        )
        .reset_index()
        .sort_values("monthly_revenue_at_risk", ascending=False)
    )

    by_action = (
        active.groupby("primary_recommendation")
        .agg(
            customers=("unified_customer_id", "count"),
            avg_churn_probability=("predicted_churn_probability", "mean"),
            monthly_revenue_at_risk=("expected_monthly_revenue_loss", "sum"),
            campaign_cost=("estimated_action_cost", "sum"),
            net_monthly_recovery_potential=("net_recovery_potential", "sum"),
            annualized_recovery_potential=("annualized_recovery_potential", "sum"),
        )
        .reset_index()
        .sort_values("net_monthly_recovery_potential", ascending=False)
    )

    top_customers = active.sort_values(
        ["monthly_revenue_at_risk", "predicted_churn_probability"],
        ascending=[False, False],
    ).head(100)

    return {
        "business_impact_by_value_segment.csv": by_value,
        "business_impact_by_risk_segment.csv": by_risk,
        "business_impact_by_recommendation.csv": by_action,
        "top_revenue_at_risk_customers.csv": top_customers,
    }


def save_barplot(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    xlabel: str,
    ylabel: str,
    file_name: str,
    color: str = "#3A7D7C",
) -> None:
    """Save a standard executive bar chart."""
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x=x, y=y, color=color)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / file_name, dpi=160)
    plt.close()


def create_visualizations(
    scenario_summary: pd.DataFrame,
    segment_tables: Dict[str, pd.DataFrame],
) -> None:
    """Create BI-focused impact visualizations."""
    sns.set_theme(style="whitegrid", context="talk")

    save_barplot(
        segment_tables["business_impact_by_risk_segment.csv"],
        "churn_risk_segment",
        "monthly_revenue_at_risk",
        "Monthly Revenue at Risk by Churn Segment",
        "Risk segment",
        "Monthly revenue at risk",
        "business_impact_revenue_at_risk_by_segment.png",
        color="#C44E52",
    )

    save_barplot(
        scenario_summary,
        "scenario",
        "gross_monthly_revenue_saved",
        "Scenario Revenue Saved Comparison",
        "Scenario",
        "Gross monthly revenue saved",
        "business_impact_revenue_saved_by_scenario.png",
        color="#4C78A8",
    )

    save_barplot(
        scenario_summary.fillna({"estimated_roi_pct": 0}),
        "scenario",
        "estimated_roi_pct",
        "Estimated ROI by Retention Scenario",
        "Scenario",
        "Estimated ROI (%)",
        "business_impact_roi_by_scenario.png",
        color="#59A14F",
    )

    value = segment_tables["business_impact_by_value_segment.csv"]
    plt.figure(figsize=(10, 6))
    value_sorted = value.sort_values("expected_clv_at_risk", ascending=False)
    sns.barplot(data=value_sorted, x="customer_value_segment", y="expected_clv_at_risk", color="#B07AA1")
    plt.title("Customer Lifetime Value at Risk by Value Segment")
    plt.xlabel("Customer value segment")
    plt.ylabel("Expected CLV at risk")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "business_impact_customer_segment_clv_at_risk.png", dpi=160)
    plt.close()


def write_business_report(
    kpis: pd.DataFrame,
    scenario_summary: pd.DataFrame,
    segment_tables: Dict[str, pd.DataFrame],
) -> None:
    """Write the final business impact simulator report."""
    kpi_lookup = dict(zip(kpis["kpi"], kpis["value"]))
    best_scenario = scenario_summary.sort_values("net_monthly_revenue_saved", ascending=False).iloc[0]

    markdown = f"""# Business Impact Simulator Report

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

{dataframe_to_markdown(kpis, max_rows=20)}

## Scenario Summary

{dataframe_to_markdown(scenario_summary, max_rows=10)}

The strongest scenario by net monthly revenue saved is **{best_scenario['scenario']}**
with estimated net monthly savings of **{best_scenario['net_monthly_revenue_saved']:,.2f}**
and annualized net savings of **{best_scenario['annualized_net_revenue_saved']:,.2f}**.

## Segment Impact

### By Risk Segment

{dataframe_to_markdown(segment_tables['business_impact_by_risk_segment.csv'], max_rows=10)}

### By Customer Value Segment

{dataframe_to_markdown(segment_tables['business_impact_by_value_segment.csv'], max_rows=10)}

### By Recommendation Type

{dataframe_to_markdown(segment_tables['business_impact_by_recommendation.csv'], max_rows=15)}

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

- Active monthly revenue at risk: `{kpi_lookup['monthly_revenue_at_risk']:,.2f}`
- Active annual revenue at risk: `{kpi_lookup['annual_revenue_at_risk']:,.2f}`
- Customer lifetime value at risk: `{kpi_lookup['customer_lifetime_value_at_risk']:,.2f}`
- Net monthly recovery potential: `{kpi_lookup['net_monthly_recovery_potential']:,.2f}`
- Annualized net recovery potential: `{kpi_lookup['annualized_net_recovery_potential']:,.2f}`

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
"""
    (REPORTS_DIR / "business_impact_simulator_report.md").write_text(markdown, encoding="utf-8")


def run_workflow() -> None:
    """Run the complete business impact simulation workflow."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    predictions, actions, features = load_inputs()
    enriched = enrich_financial_metrics(actions, features)
    kpis = build_kpi_summary(enriched, predictions)
    scenario_summary = simulate_scenarios(enriched)
    segment_tables = build_segment_summaries(enriched)

    kpis.to_csv(REPORTS_DIR / "business_impact_kpi_summary.csv", index=False)
    scenario_summary.to_csv(REPORTS_DIR / "business_impact_scenario_summary.csv", index=False)
    for file_name, table in segment_tables.items():
        table.to_csv(REPORTS_DIR / file_name, index=False)

    create_visualizations(scenario_summary, segment_tables)
    write_business_report(kpis, scenario_summary, segment_tables)

    print("Business impact simulator workflow complete.")
    print(f"Scenario rows: {len(scenario_summary):,}")
    print(f"Monthly revenue at risk: {kpis.loc[kpis['kpi'].eq('monthly_revenue_at_risk'), 'value'].iloc[0]:,.2f}")
    print(f"Best scenario: {scenario_summary.sort_values('net_monthly_revenue_saved', ascending=False).iloc[0]['scenario']}")


if __name__ == "__main__":
    run_workflow()
