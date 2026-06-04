/*
Business purpose:
Prioritize retained customers who are not churned yet but show risk signals.
Use this as a SQL-only retention opportunity list for stakeholder reporting.
*/

WITH active_customers AS (
    SELECT
        unified_customer_id,
        contract_type,
        customer_value_segment,
        tenure,
        tenure_segment,
        monthly_charges,
        estimated_customer_lifetime_value,
        payment_risk_score,
        engagement_score,
        support_burden_score,
        customer_health_score,
        inactivity_days,
        support_ticket_count,
        open_ticket_count,
        complaint_frequency,
        CASE
            WHEN customer_value_segment = 'high_value' THEN 1.30
            WHEN customer_value_segment = 'established_value' THEN 1.10
            WHEN customer_value_segment = 'emerging_value' THEN 0.95
            ELSE 0.80
        END AS value_multiplier
    FROM vw_churn_customer_analytics
    WHERE churn_label = 0
),
opportunity_scoring AS (
    SELECT
        *,
        CASE WHEN contract_type = 'month_to_month' THEN 20 ELSE 0 END
      + CASE WHEN tenure <= 12 THEN 20 ELSE 0 END
      + CASE WHEN payment_risk_score >= 0.70 THEN 15 ELSE 0 END
      + CASE WHEN engagement_score < 0.35 OR inactivity_days > 90 THEN 15 ELSE 0 END
      + CASE WHEN support_burden_score >= 0.45 OR open_ticket_count > 0 THEN 15 ELSE 0 END
      + CASE WHEN customer_value_segment IN ('high_value', 'established_value') THEN 10 ELSE 0 END
      + CASE WHEN complaint_frequency >= 0.50 THEN 5 ELSE 0 END AS retention_opportunity_score
    FROM active_customers
),
prioritized AS (
    SELECT
        *,
        monthly_charges * (retention_opportunity_score / 100.0) AS estimated_monthly_revenue_at_risk,
        estimated_customer_lifetime_value * (retention_opportunity_score / 100.0) AS estimated_clv_at_risk,
        ROW_NUMBER() OVER (
            ORDER BY retention_opportunity_score DESC, monthly_charges DESC, estimated_customer_lifetime_value DESC
        ) AS retention_action_rank,
        NTILE(20) OVER (
            ORDER BY retention_opportunity_score DESC, monthly_charges DESC
        ) AS retention_priority_bucket
    FROM opportunity_scoring
)
SELECT
    retention_action_rank,
    retention_priority_bucket,
    unified_customer_id,
    CASE
        WHEN retention_opportunity_score >= 70 THEN 'P1_high'
        WHEN retention_opportunity_score >= 40 THEN 'P2_medium'
        ELSE 'P3_monitor'
    END AS retention_priority,
    retention_opportunity_score,
    contract_type,
    customer_value_segment,
    tenure,
    tenure_segment,
    ROUND(monthly_charges, 2) AS monthly_charges,
    ROUND(estimated_monthly_revenue_at_risk, 2) AS estimated_monthly_revenue_at_risk,
    ROUND(estimated_clv_at_risk, 2) AS estimated_clv_at_risk,
    ROUND(customer_health_score, 4) AS customer_health_score,
    ROUND(engagement_score, 4) AS engagement_score,
    ROUND(support_burden_score, 4) AS support_burden_score,
    ROUND(payment_risk_score, 4) AS payment_risk_score,
    inactivity_days,
    support_ticket_count,
    open_ticket_count,
    ROUND(complaint_frequency, 4) AS complaint_frequency
FROM prioritized
WHERE retention_opportunity_score >= 40
ORDER BY retention_action_rank;
