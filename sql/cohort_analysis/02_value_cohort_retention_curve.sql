/*
Business purpose:
Build a cohort-style retention curve by value segment and tenure month.
This is useful for lifecycle reporting even when the source is a customer-level
snapshot rather than a monthly event table.
*/

WITH customer_tenure AS (
    SELECT
        unified_customer_id,
        churn_label,
        customer_value_segment,
        contract_type,
        tenure,
        monthly_charges
    FROM vw_churn_customer_analytics
),
cohort_months AS (
    SELECT
        customer_value_segment,
        contract_type,
        tenure AS tenure_month,
        COUNT(*) AS customers_reaching_month,
        SUM(churn_label) AS churned_customers,
        AVG(churn_label * 1.0) AS churn_rate_at_tenure,
        SUM(monthly_charges) AS monthly_revenue_reaching_month
    FROM customer_tenure
    GROUP BY
        customer_value_segment,
        contract_type,
        tenure
),
retention_curve AS (
    SELECT
        *,
        FIRST_VALUE(customers_reaching_month) OVER (
            PARTITION BY customer_value_segment, contract_type
            ORDER BY tenure_month
        ) AS starting_customers,
        SUM(churned_customers) OVER (
            PARTITION BY customer_value_segment, contract_type
            ORDER BY tenure_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_churned_customers
    FROM cohort_months
)
SELECT
    customer_value_segment,
    contract_type,
    tenure_month,
    customers_reaching_month,
    starting_customers,
    churned_customers,
    cumulative_churned_customers,
    ROUND(churn_rate_at_tenure * 100, 2) AS churn_rate_at_tenure_pct,
    ROUND(1 - (cumulative_churned_customers * 1.0 / NULLIF(starting_customers, 0)), 4) AS cumulative_retention_rate,
    ROUND(monthly_revenue_reaching_month, 2) AS monthly_revenue_reaching_month
FROM retention_curve
WHERE starting_customers >= 20
ORDER BY customer_value_segment, contract_type, tenure_month;
