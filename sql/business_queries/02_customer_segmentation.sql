/*
Business purpose:
Segment customers by lifecycle, value, contract, payment risk, engagement, and
support burden. This helps stakeholders identify where churn concentrates.
*/

WITH segmented_customers AS (
    SELECT
        unified_customer_id,
        churn_label,
        contract_type,
        tenure_segment,
        customer_value_segment,
        payment_risk_segment,
        engagement_segment,
        support_burden_segment,
        customer_health_segment,
        monthly_charges,
        estimated_customer_lifetime_value
    FROM vw_churn_customer_analytics
),
segment_summary AS (
    SELECT
        contract_type,
        tenure_segment,
        customer_value_segment,
        payment_risk_segment,
        engagement_segment,
        support_burden_segment,
        COUNT(*) AS customers,
        SUM(churn_label) AS churned_customers,
        AVG(churn_label * 1.0) AS churn_rate,
        AVG(monthly_charges) AS avg_monthly_charges,
        SUM(monthly_charges) AS monthly_revenue_base,
        AVG(estimated_customer_lifetime_value) AS avg_clv_indicator
    FROM segmented_customers
    GROUP BY
        contract_type,
        tenure_segment,
        customer_value_segment,
        payment_risk_segment,
        engagement_segment,
        support_burden_segment
),
ranked_segments AS (
    SELECT
        *,
        RANK() OVER (ORDER BY churn_rate DESC, customers DESC) AS churn_risk_rank,
        RANK() OVER (ORDER BY monthly_revenue_base DESC) AS revenue_scale_rank
    FROM segment_summary
)
SELECT
    contract_type,
    tenure_segment,
    customer_value_segment,
    payment_risk_segment,
    engagement_segment,
    support_burden_segment,
    customers,
    churned_customers,
    ROUND(churn_rate * 100, 2) AS churn_rate_pct,
    ROUND(avg_monthly_charges, 2) AS avg_monthly_charges,
    ROUND(monthly_revenue_base, 2) AS monthly_revenue_base,
    ROUND(avg_clv_indicator, 2) AS avg_clv_indicator,
    churn_risk_rank,
    revenue_scale_rank
FROM ranked_segments
WHERE customers >= 20
ORDER BY churn_risk_rank, revenue_scale_rank;
