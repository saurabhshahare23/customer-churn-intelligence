/*
Business purpose:
Compare churn and value by engagement cohort. This supports reactivation
campaign design for customers with weak activity signals.
*/

WITH engagement_cohorts AS (
    SELECT
        unified_customer_id,
        churn_label,
        engagement_segment,
        activity_status,
        customer_value_segment,
        CASE
            WHEN invoice_count = 0 THEN 'no_purchase_activity'
            WHEN invoice_count <= 3 THEN 'low_frequency'
            WHEN invoice_count <= 10 THEN 'moderate_frequency'
            ELSE 'high_frequency'
        END AS frequency_cohort,
        CASE
            WHEN inactivity_days > 180 OR no_activity_flag = 1 THEN 'dormant'
            WHEN inactivity_days > 90 THEN 'at_risk_inactive'
            WHEN inactivity_days > 30 THEN 'recently_active'
            ELSE 'currently_active'
        END AS recency_cohort,
        monthly_charges,
        net_activity_revenue,
        estimated_customer_lifetime_value
    FROM vw_churn_customer_analytics
),
cohort_summary AS (
    SELECT
        engagement_segment,
        activity_status,
        frequency_cohort,
        recency_cohort,
        customer_value_segment,
        COUNT(*) AS customers,
        SUM(churn_label) AS churned_customers,
        AVG(churn_label * 1.0) AS churn_rate,
        AVG(monthly_charges) AS avg_monthly_charges,
        AVG(net_activity_revenue) AS avg_activity_revenue,
        SUM(estimated_customer_lifetime_value * churn_label) AS clv_lost_to_churn
    FROM engagement_cohorts
    GROUP BY
        engagement_segment,
        activity_status,
        frequency_cohort,
        recency_cohort,
        customer_value_segment
)
SELECT
    engagement_segment,
    activity_status,
    frequency_cohort,
    recency_cohort,
    customer_value_segment,
    customers,
    churned_customers,
    ROUND(churn_rate * 100, 2) AS churn_rate_pct,
    ROUND(avg_monthly_charges, 2) AS avg_monthly_charges,
    ROUND(avg_activity_revenue, 2) AS avg_activity_revenue,
    ROUND(clv_lost_to_churn, 2) AS clv_lost_to_churn,
    RANK() OVER (ORDER BY churn_rate DESC, clv_lost_to_churn DESC) AS cohort_priority_rank
FROM cohort_summary
WHERE customers >= 10
ORDER BY cohort_priority_rank;
