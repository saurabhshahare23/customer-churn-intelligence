/*
Business purpose:
Measure retained customer base and revenue by contract and value segment.
This supports retention health reporting and customer success planning.
*/

WITH retention_base AS (
    SELECT
        unified_customer_id,
        churn_label,
        contract_type,
        customer_value_segment,
        tenure_segment,
        payment_risk_segment,
        monthly_charges,
        estimated_customer_lifetime_value,
        customer_health_score
    FROM vw_churn_customer_analytics
),
summary AS (
    SELECT
        contract_type,
        customer_value_segment,
        tenure_segment,
        payment_risk_segment,
        COUNT(*) AS customers,
        SUM(CASE WHEN churn_label = 0 THEN 1 ELSE 0 END) AS retained_customers,
        SUM(CASE WHEN churn_label = 1 THEN 1 ELSE 0 END) AS churned_customers,
        AVG(CASE WHEN churn_label = 0 THEN monthly_charges END) AS retained_arpu,
        SUM(CASE WHEN churn_label = 0 THEN monthly_charges ELSE 0 END) AS retained_monthly_revenue,
        SUM(CASE WHEN churn_label = 0 THEN estimated_customer_lifetime_value ELSE 0 END) AS retained_clv_indicator,
        AVG(customer_health_score) AS avg_customer_health_score
    FROM retention_base
    GROUP BY
        contract_type,
        customer_value_segment,
        tenure_segment,
        payment_risk_segment
)
SELECT
    contract_type,
    customer_value_segment,
    tenure_segment,
    payment_risk_segment,
    customers,
    retained_customers,
    churned_customers,
    ROUND(retained_customers * 100.0 / NULLIF(customers, 0), 2) AS retention_rate_pct,
    ROUND(retained_arpu, 2) AS retained_arpu,
    ROUND(retained_monthly_revenue, 2) AS retained_monthly_revenue,
    ROUND(retained_clv_indicator, 2) AS retained_clv_indicator,
    ROUND(avg_customer_health_score, 4) AS avg_customer_health_score,
    RANK() OVER (ORDER BY retained_monthly_revenue DESC) AS retained_revenue_rank
FROM summary
WHERE customers >= 10
ORDER BY retained_revenue_rank;
