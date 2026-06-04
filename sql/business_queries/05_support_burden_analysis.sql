/*
Business purpose:
Measure how customer support friction relates to churn, revenue, and customer
experience. Use this for service recovery and support operations planning.
*/

WITH support_base AS (
    SELECT
        unified_customer_id,
        churn_label,
        support_burden_segment,
        customer_value_segment,
        support_ticket_count,
        open_ticket_count,
        critical_ticket_count,
        low_satisfaction_ticket_count,
        complaint_ticket_count,
        complaint_frequency,
        avg_satisfaction_rating,
        avg_resolution_hours,
        monthly_charges,
        estimated_customer_lifetime_value,
        CASE
            WHEN support_ticket_count >= 5 THEN '5_plus_tickets'
            WHEN support_ticket_count >= 3 THEN '3_4_tickets'
            WHEN support_ticket_count >= 1 THEN '1_2_tickets'
            ELSE 'no_tickets'
        END AS support_volume_band
    FROM vw_churn_customer_analytics
),
support_summary AS (
    SELECT
        support_burden_segment,
        support_volume_band,
        customer_value_segment,
        COUNT(*) AS customers,
        SUM(churn_label) AS churned_customers,
        AVG(churn_label * 1.0) AS churn_rate,
        AVG(support_ticket_count) AS avg_support_tickets,
        AVG(open_ticket_count) AS avg_open_tickets,
        AVG(critical_ticket_count) AS avg_critical_tickets,
        AVG(complaint_frequency) AS avg_complaint_frequency,
        AVG(avg_satisfaction_rating) AS avg_satisfaction_rating,
        AVG(avg_resolution_hours) AS avg_resolution_hours,
        SUM(monthly_charges) AS monthly_revenue_base,
        SUM(estimated_customer_lifetime_value * churn_label) AS clv_lost_to_churn
    FROM support_base
    GROUP BY
        support_burden_segment,
        support_volume_band,
        customer_value_segment
)
SELECT
    support_burden_segment,
    support_volume_band,
    customer_value_segment,
    customers,
    churned_customers,
    ROUND(churn_rate * 100, 2) AS churn_rate_pct,
    ROUND(avg_support_tickets, 2) AS avg_support_tickets,
    ROUND(avg_open_tickets, 2) AS avg_open_tickets,
    ROUND(avg_critical_tickets, 2) AS avg_critical_tickets,
    ROUND(avg_complaint_frequency, 4) AS avg_complaint_frequency,
    ROUND(avg_satisfaction_rating, 2) AS avg_satisfaction_rating,
    ROUND(avg_resolution_hours, 2) AS avg_resolution_hours,
    ROUND(monthly_revenue_base, 2) AS monthly_revenue_base,
    ROUND(clv_lost_to_churn, 2) AS clv_lost_to_churn,
    RANK() OVER (ORDER BY churn_rate DESC, monthly_revenue_base DESC) AS support_risk_rank
FROM support_summary
WHERE customers >= 10
ORDER BY support_risk_rank;
