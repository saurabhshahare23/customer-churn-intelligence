/*
Business purpose:
Identify customers with the strongest rule-based churn risk profile and quantify
revenue exposure. Use this for retention outreach prioritization.

Note:
This query uses analytical risk rules from churn_features_master, not model
probabilities. Model-scored action tables can be layered on top separately.
*/

WITH customer_risk AS (
    SELECT
        unified_customer_id,
        churn_label,
        contract_type,
        tenure,
        tenure_segment,
        customer_value_segment,
        payment_method_type,
        monthly_charges,
        estimated_customer_lifetime_value,
        inactivity_days,
        engagement_score,
        support_burden_score,
        payment_risk_score,
        customer_health_score,
        open_ticket_count,
        critical_ticket_count,
        complaint_frequency,
        CASE
            WHEN churn_label = 1 THEN 0
            ELSE
                CASE WHEN contract_type = 'month_to_month' THEN 20 ELSE 0 END
              + CASE WHEN tenure <= 12 THEN 20 ELSE 0 END
              + CASE WHEN payment_risk_score >= 0.70 THEN 15 ELSE 0 END
              + CASE WHEN engagement_score < 0.35 OR inactivity_days > 90 THEN 15 ELSE 0 END
              + CASE WHEN support_burden_score >= 0.45 OR open_ticket_count > 0 THEN 15 ELSE 0 END
              + CASE WHEN customer_value_segment IN ('high_value', 'established_value') THEN 10 ELSE 0 END
              + CASE WHEN complaint_frequency >= 0.50 OR critical_ticket_count > 0 THEN 5 ELSE 0 END
        END AS business_risk_score
    FROM vw_churn_customer_analytics
),
ranked_customers AS (
    SELECT
        *,
        monthly_charges * (business_risk_score / 100.0) AS monthly_revenue_at_risk,
        estimated_customer_lifetime_value * (business_risk_score / 100.0) AS clv_at_risk,
        CASE
            WHEN business_risk_score >= 70 THEN 'high_risk'
            WHEN business_risk_score >= 40 THEN 'medium_risk'
            ELSE 'low_risk'
        END AS analytical_risk_segment,
        ROW_NUMBER() OVER (
            ORDER BY business_risk_score DESC, monthly_charges DESC, estimated_customer_lifetime_value DESC
        ) AS outreach_rank,
        NTILE(10) OVER (
            ORDER BY business_risk_score DESC, monthly_charges DESC
        ) AS risk_decile
    FROM customer_risk
    WHERE churn_label = 0
)
SELECT
    outreach_rank,
    risk_decile,
    unified_customer_id,
    analytical_risk_segment,
    business_risk_score,
    contract_type,
    tenure,
    tenure_segment,
    customer_value_segment,
    payment_method_type,
    ROUND(monthly_charges, 2) AS monthly_charges,
    ROUND(monthly_revenue_at_risk, 2) AS monthly_revenue_at_risk,
    ROUND(clv_at_risk, 2) AS clv_at_risk,
    inactivity_days,
    ROUND(engagement_score, 4) AS engagement_score,
    ROUND(support_burden_score, 4) AS support_burden_score,
    ROUND(payment_risk_score, 4) AS payment_risk_score,
    ROUND(customer_health_score, 4) AS customer_health_score
FROM ranked_customers
WHERE analytical_risk_segment IN ('high_risk', 'medium_risk')
ORDER BY outreach_rank;
