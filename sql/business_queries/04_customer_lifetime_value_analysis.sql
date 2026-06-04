/*
Business purpose:
Analyze lifetime value concentration and churn impact by value segment.
Use this to protect valuable customer groups and size financial exposure.
*/

WITH value_base AS (
    SELECT
        unified_customer_id,
        churn_label,
        customer_value_segment,
        tenure_segment,
        contract_type,
        monthly_charges,
        avg_monthly_spend,
        estimated_customer_lifetime_value,
        customer_health_score,
        PERCENT_RANK() OVER (ORDER BY estimated_customer_lifetime_value) AS clv_percentile
    FROM vw_churn_customer_analytics
),
value_ranked AS (
    SELECT
        *,
        CASE
            WHEN clv_percentile >= 0.90 THEN 'top_10_pct_clv'
            WHEN clv_percentile >= 0.75 THEN 'top_25_pct_clv'
            WHEN clv_percentile >= 0.50 THEN 'mid_clv'
            ELSE 'lower_clv'
        END AS clv_tier
    FROM value_base
),
summary AS (
    SELECT
        customer_value_segment,
        clv_tier,
        tenure_segment,
        contract_type,
        COUNT(*) AS customers,
        SUM(churn_label) AS churned_customers,
        AVG(churn_label * 1.0) AS churn_rate,
        AVG(monthly_charges) AS avg_monthly_charges,
        AVG(avg_monthly_spend) AS avg_monthly_spend,
        SUM(estimated_customer_lifetime_value) AS total_clv_indicator,
        SUM(estimated_customer_lifetime_value * churn_label) AS clv_lost_to_churn,
        AVG(customer_health_score) AS avg_customer_health_score
    FROM value_ranked
    GROUP BY
        customer_value_segment,
        clv_tier,
        tenure_segment,
        contract_type
)
SELECT
    customer_value_segment,
    clv_tier,
    tenure_segment,
    contract_type,
    customers,
    churned_customers,
    ROUND(churn_rate * 100, 2) AS churn_rate_pct,
    ROUND(avg_monthly_charges, 2) AS avg_monthly_charges,
    ROUND(avg_monthly_spend, 2) AS avg_monthly_spend,
    ROUND(total_clv_indicator, 2) AS total_clv_indicator,
    ROUND(clv_lost_to_churn, 2) AS clv_lost_to_churn,
    ROUND(avg_customer_health_score, 4) AS avg_customer_health_score,
    RANK() OVER (ORDER BY clv_lost_to_churn DESC) AS clv_loss_rank
FROM summary
WHERE customers >= 10
ORDER BY clv_loss_rank;
