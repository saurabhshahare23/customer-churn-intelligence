/*
Business purpose:
Executive KPI snapshot for churn, retention, revenue at risk, and average value.
Use this query for monthly leadership reporting and top-line customer health.
*/

WITH customer_base AS (
    SELECT *
    FROM vw_churn_customer_analytics
),
kpis AS (
    SELECT
        COUNT(*) AS total_customers,
        SUM(churn_label) AS churned_customers,
        COUNT(*) - SUM(churn_label) AS retained_customers,
        AVG(churn_label * 1.0) AS churn_rate,
        1 - AVG(churn_label * 1.0) AS retention_rate,
        AVG(monthly_charges) AS average_revenue_per_user,
        AVG(estimated_customer_lifetime_value) AS avg_clv_indicator,
        SUM(realized_monthly_revenue_lost) AS realized_monthly_revenue_lost,
        SUM(realized_clv_lost) AS realized_clv_lost
    FROM customer_base
)
SELECT
    total_customers,
    churned_customers,
    retained_customers,
    ROUND(churn_rate * 100, 2) AS churn_rate_pct,
    ROUND(retention_rate * 100, 2) AS retention_rate_pct,
    ROUND(average_revenue_per_user, 2) AS arpu,
    ROUND(avg_clv_indicator, 2) AS avg_clv_indicator,
    ROUND(realized_monthly_revenue_lost, 2) AS realized_monthly_revenue_lost,
    ROUND(realized_clv_lost, 2) AS realized_clv_lost
FROM kpis;
