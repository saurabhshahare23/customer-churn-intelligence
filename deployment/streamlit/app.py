"""Minimal Streamlit app for Customer Churn Intelligence.

Run from the project root:
    streamlit run deployment/streamlit/app.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except ImportError:  # Plotly is optional; the app falls back to Streamlit charts.
    px = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "churn_features_master.csv"
RETENTION_ACTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "customer_retention_actions.csv"
REPORT_ACTIONS_PATH = PROJECT_ROOT / "reports" / "business_reports" / "customer_retention_actions.csv"
PREDICTIONS_PATH = PROJECT_ROOT / "models" / "model_metrics" / "best_model_test_predictions.csv"
BUSINESS_IMPACT_KPI_PATH = PROJECT_ROOT / "reports" / "business_reports" / "business_impact_kpi_summary.csv"


st.set_page_config(
    page_title="Customer Churn Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    """Load a CSV with a clear error if the artifact is missing."""
    if not path.exists():
        raise FileNotFoundError(f"Required artifact not found: {path}")
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_optional_csv(path: Path) -> Optional[pd.DataFrame]:
    """Load an optional CSV artifact if it exists."""
    if not path.exists():
        return None
    return pd.read_csv(path)


def load_retention_actions() -> pd.DataFrame:
    """Load the customer action table from processed data or report outputs."""
    if RETENTION_ACTIONS_PATH.exists():
        return load_csv(RETENTION_ACTIONS_PATH)
    return load_csv(REPORT_ACTIONS_PATH)


def format_currency(value: float) -> str:
    """Format numeric values as compact currency strings."""
    return f"${value:,.2f}"


def format_percent(value: float) -> str:
    """Format decimal probabilities as percentages."""
    return f"{value * 100:.1f}%"


def risk_badge(risk_level: str) -> None:
    """Display risk level with a simple visual treatment."""
    colors = {
        "high risk": "#B42318",
        "medium risk": "#B54708",
        "low risk": "#027A48",
    }
    color = colors.get(str(risk_level).lower(), "#344054")
    st.markdown(
        f"""
        <div style="padding: 0.55rem 0.8rem; border-radius: 0.4rem;
                    background: {color}; color: white; font-weight: 700;
                    text-align: center;">
            {str(risk_level).upper()}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_bar_chart(df: pd.DataFrame, x: str, y: str, title: str) -> None:
    """Render a bar chart using Plotly when available, otherwise Streamlit."""
    if px is not None:
        fig = px.bar(df, x=x, y=y, title=title, text_auto=".2s")
        fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), height=360)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.subheader(title)
        st.bar_chart(df.set_index(x)[y])


def render_histogram(df: pd.DataFrame, column: str, title: str) -> None:
    """Render a histogram using Plotly when available, otherwise Streamlit."""
    if px is not None:
        fig = px.histogram(df, x=column, nbins=30, title=title)
        fig.update_layout(margin=dict(l=10, r=10, t=55, b=10), height=360)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.subheader(title)
        st.bar_chart(df[column].round(2).value_counts().sort_index())


def main() -> None:
    """Build the Streamlit churn intelligence experience."""
    st.title("Customer Churn Intelligence")
    st.caption("A lightweight business view of churn risk, revenue exposure, and retention actions.")

    try:
        actions = load_retention_actions()
        features = load_csv(FEATURES_PATH)
        predictions = load_optional_csv(PREDICTIONS_PATH)
        business_kpis = load_optional_csv(BUSINESS_IMPACT_KPI_PATH)
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Unable to load app data: {exc}")
        st.stop()

    required_columns = {
        "unified_customer_id",
        "predicted_churn_probability",
        "churn_risk_segment",
        "customer_value_segment",
        "monthly_revenue_at_risk",
        "primary_recommendation",
        "retention_priority",
    }
    missing_columns = sorted(required_columns - set(actions.columns))
    if missing_columns:
        st.error(f"customer_retention_actions.csv is missing required columns: {missing_columns}")
        st.stop()

    active_actions = actions.loc[actions.get("action_status", "active_retention").eq("active_retention")].copy()
    if active_actions.empty:
        active_actions = actions.copy()

    st.sidebar.header("Customer Lookup")
    customer_ids = actions["unified_customer_id"].sort_values().tolist()
    default_index = 0
    high_risk_ids = actions.loc[
        actions["churn_risk_segment"].eq("high risk"), "unified_customer_id"
    ].tolist()
    if high_risk_ids:
        default_index = customer_ids.index(high_risk_ids[0])

    selected_customer = st.sidebar.selectbox(
        "Customer ID",
        customer_ids,
        index=default_index,
        help="Select a unified customer identifier to inspect retention action details.",
    )

    st.sidebar.divider()
    risk_filter = st.sidebar.multiselect(
        "Risk segment",
        options=sorted(actions["churn_risk_segment"].dropna().unique().tolist()),
        default=sorted(actions["churn_risk_segment"].dropna().unique().tolist()),
    )
    filtered_actions = actions.loc[actions["churn_risk_segment"].isin(risk_filter)].copy()

    total_customers = len(actions)
    high_risk_customers = int(actions["churn_risk_segment"].eq("high risk").sum())
    total_revenue_at_risk = float(active_actions["monthly_revenue_at_risk"].sum())
    estimated_recovery = float(
        active_actions.get("estimated_net_mrr_impact", pd.Series(dtype=float)).sum()
    )

    if business_kpis is not None and {"kpi", "value"}.issubset(business_kpis.columns):
        kpi_lookup = dict(zip(business_kpis["kpi"], business_kpis["value"]))
        total_revenue_at_risk = float(kpi_lookup.get("monthly_revenue_at_risk", total_revenue_at_risk))
        estimated_recovery = float(kpi_lookup.get("net_monthly_recovery_potential", estimated_recovery))

    kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
    kpi_1.metric("Total Customers", f"{total_customers:,}")
    kpi_2.metric("High-Risk Customers", f"{high_risk_customers:,}")
    kpi_3.metric("Monthly Revenue at Risk", format_currency(total_revenue_at_risk))
    kpi_4.metric("Estimated Monthly Recovery", format_currency(estimated_recovery))

    st.divider()

    selected_row = actions.loc[actions["unified_customer_id"].eq(selected_customer)].iloc[0]
    customer_feature = features.loc[features["unified_customer_id"].eq(selected_customer)]

    st.subheader("Customer Risk Profile")
    profile_left, profile_right = st.columns([1, 2])

    with profile_left:
        risk_badge(selected_row["churn_risk_segment"])
        st.metric("Churn Probability", format_percent(float(selected_row["predicted_churn_probability"])))
        st.metric("Revenue at Risk", format_currency(float(selected_row["monthly_revenue_at_risk"])))

    with profile_right:
        detail_cols = st.columns(3)
        detail_cols[0].metric("Customer Segment", str(selected_row["customer_value_segment"]).replace("_", " ").title())
        detail_cols[1].metric("Recommendation Priority", str(selected_row["retention_priority"]))
        detail_cols[2].metric("Monthly Charges", format_currency(float(selected_row.get("monthly_charges", 0))))

        st.markdown("**Recommended Retention Action**")
        st.write(str(selected_row["primary_recommendation"]).replace("_", " ").title())
        st.caption(str(selected_row.get("recommendation_reason", "No recommendation reason available.")))

    with st.expander("Customer details", expanded=False):
        display_columns = [
            "unified_customer_id",
            "action_status",
            "tenure",
            "tenure_segment",
            "contract",
            "payment_method",
            "activity_status",
            "engagement_score",
            "customer_health_score",
            "support_ticket_count",
            "complaint_frequency",
            "support_burden_score",
            "risk_driver_summary",
            "secondary_recommendation",
        ]
        available_display_columns = [col for col in display_columns if col in actions.columns]
        st.dataframe(selected_row[available_display_columns].to_frame("value"), use_container_width=True)

        if not customer_feature.empty:
            st.caption("Selected feature snapshot")
            feature_cols = [
                "churn_label",
                "tenure",
                "monthly_charges",
                "estimated_customer_lifetime_value",
                "inactivity_days",
                "engagement_score",
                "support_burden_score",
                "payment_risk_score",
                "customer_health_score",
            ]
            available_feature_cols = [col for col in feature_cols if col in customer_feature.columns]
            st.dataframe(customer_feature[available_feature_cols], use_container_width=True)

    st.divider()
    st.subheader("Portfolio View")

    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        risk_counts = (
            filtered_actions.groupby("churn_risk_segment")
            .size()
            .reset_index(name="customers")
            .sort_values("customers", ascending=False)
        )
        render_bar_chart(risk_counts, "churn_risk_segment", "customers", "Risk Distribution")

    with chart_col_2:
        render_histogram(filtered_actions, "predicted_churn_probability", "Churn Probability Distribution")

    revenue_by_segment = (
        filtered_actions.groupby("customer_value_segment", dropna=False)["monthly_revenue_at_risk"]
        .sum()
        .reset_index()
        .sort_values("monthly_revenue_at_risk", ascending=False)
    )
    render_bar_chart(
        revenue_by_segment,
        "customer_value_segment",
        "monthly_revenue_at_risk",
        "Revenue at Risk by Customer Segment",
    )

    st.subheader("Action Queue")
    queue_columns = [
        "unified_customer_id",
        "churn_risk_segment",
        "predicted_churn_probability",
        "customer_value_segment",
        "monthly_revenue_at_risk",
        "primary_recommendation",
        "retention_priority",
    ]
    st.dataframe(
        filtered_actions[queue_columns]
        .sort_values(["churn_risk_segment", "predicted_churn_probability"], ascending=[True, False])
        .head(100),
        use_container_width=True,
        hide_index=True,
    )

    if predictions is not None:
        st.caption(f"Model prediction output loaded: {len(predictions):,} holdout prediction rows.")


if __name__ == "__main__":
    main()
