/*
Business purpose:
Understand how inactivity, purchase frequency, and engagement score relate to
churn and revenue. Use this to design reactivation campaigns.
*/

WITH engagement_base AS (
    SELECT
        unified_customer_id,
        churn_label,
        engagement_segment,
        activity_status,
        customer_value_segment,
        inactivity_days,
        engagement_score,
        recency_frequency_metrics,
        invoice_count,
        activity_line_count,
        net_activity_revenue,
        gross_activity_revenue,
        monthly_charges,
        estimated_customer_lifetime_value,
        CASE
            WHEN inactivity_days > 180 OR no_activity_flag = 1 THEN 'inactive_180_plus_days'
            WHEN inactivity_days > 90 THEN 'inactive_91_180_days'
            WHEN inactivity_days > 30 THEN 'active_31_90_days'
            ELSE 'active_0_30_days'
        END AS inactivity_band
    FROM vw_churn_customer_analytics
),
engagement_summary AS (
    SELECT
        engagement_segment,
        activity_status,
        inactivity_band,
        customer_value_segment,
        COUNT(*) AS customers,
        SUM(churn_label) AS churned_customers,
        AVG(churn_label * 1.0) AS churn_rate,
        AVG(inactivity_days) AS avg_inactivity_days,
        AVG(engagement_score) AS avg_engagement_score,
        AVG(recency_frequency_metrics) AS avg_recency_frequency_score,
        AVG(invoice_count) AS avg_invoice_count,
        AVG(net_activity_revenue) AS avg_net_activity_revenue,
        SUM(monthly_charges) AS monthly_revenue_base,
        SUM(estimated_customer_lifetime_value * churn_label) AS clv_lost_to_churn
    FROM engagement_base
    GROUP BY
        engagement_segment,
        activity_status,
        inactivity_band,
        customer_value_segment
)
SELECT
    engagement_segment,
    activity_status,
    inactivity_band,
    customer_value_segment,
    customers,
    churned_customers,
    ROUND(churn_rate * 100, 2) AS churn_rate_pct,
    ROUND(avg_inactivity_days, 2) AS avg_inactivity_days,
    ROUND(avg_engagement_score, 4) AS avg_engagement_score,
    ROUND(avg_recency_frequency_score, 4) AS avg_recency_frequency_score,
    ROUND(avg_invoice_count, 2) AS avg_invoice_count,
    ROUND(avg_net_activity_revenue, 2) AS avg_net_activity_revenue,
    ROUND(monthly_revenue_base, 2) AS monthly_revenue_base,
    ROUND(clv_lost_to_churn, 2) AS clv_lost_to_churn,
    DENSE_RANK() OVER (ORDER BY churn_rate DESC) AS engagement_risk_rank
FROM engagement_summary
WHERE customers >= 10
ORDER BY engagement_risk_rank, monthly_revenue_base DESC;
