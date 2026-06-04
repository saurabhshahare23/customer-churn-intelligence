/*
Business purpose:
Analyze churn by tenure cohort and contract type. This helps retention teams
understand which lifecycle stages need onboarding, nurture, or loyalty motions.
*/

WITH cohort_base AS (
    SELECT
        unified_customer_id,
        churn_label,
        tenure,
        tenure_segment,
        contract_type,
        customer_value_segment,
        monthly_charges,
        estimated_customer_lifetime_value,
        CASE
            WHEN tenure <= 3 THEN 'month_0_3'
            WHEN tenure <= 6 THEN 'month_4_6'
            WHEN tenure <= 12 THEN 'month_7_12'
            WHEN tenure <= 24 THEN 'year_2'
            WHEN tenure <= 48 THEN 'year_3_4'
            ELSE 'year_5_plus'
        END AS lifecycle_cohort
    FROM vw_churn_customer_analytics
),
cohort_summary AS (
    SELECT
        lifecycle_cohort,
        tenure_segment,
        contract_type,
        customer_value_segment,
        COUNT(*) AS customers,
        SUM(churn_label) AS churned_customers,
        AVG(churn_label * 1.0) AS churn_rate,
        AVG(monthly_charges) AS avg_monthly_charges,
        SUM(monthly_charges * churn_label) AS realized_monthly_revenue_lost,
        SUM(estimated_customer_lifetime_value * churn_label) AS realized_clv_lost
    FROM cohort_base
    GROUP BY
        lifecycle_cohort,
        tenure_segment,
        contract_type,
        customer_value_segment
),
ranked AS (
    SELECT
        *,
        RANK() OVER (PARTITION BY lifecycle_cohort ORDER BY churn_rate DESC, customers DESC) AS cohort_risk_rank,
        SUM(customers) OVER (PARTITION BY lifecycle_cohort) AS lifecycle_cohort_size
    FROM cohort_summary
)
SELECT
    lifecycle_cohort,
    tenure_segment,
    contract_type,
    customer_value_segment,
    customers,
    lifecycle_cohort_size,
    churned_customers,
    ROUND(churn_rate * 100, 2) AS churn_rate_pct,
    ROUND(avg_monthly_charges, 2) AS avg_monthly_charges,
    ROUND(realized_monthly_revenue_lost, 2) AS realized_monthly_revenue_lost,
    ROUND(realized_clv_lost, 2) AS realized_clv_lost,
    cohort_risk_rank
FROM ranked
WHERE customers >= 10
ORDER BY lifecycle_cohort, cohort_risk_rank;
