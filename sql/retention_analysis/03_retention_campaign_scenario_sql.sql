/*
Business purpose:
SQL-only campaign scenario simulator for retained customers. This mirrors the
business impact simulator at a simplified analytical level for BI tools.
*/

WITH retained_customers AS (
    SELECT
        unified_customer_id,
        monthly_charges,
        estimated_customer_lifetime_value,
        customer_value_segment,
        CASE
            WHEN contract_type = 'month_to_month' THEN 20 ELSE 0 END
          + CASE WHEN tenure <= 12 THEN 20 ELSE 0 END
          + CASE WHEN payment_risk_score >= 0.70 THEN 15 ELSE 0 END
          + CASE WHEN engagement_score < 0.35 OR inactivity_days > 90 THEN 15 ELSE 0 END
          + CASE WHEN support_burden_score >= 0.45 OR open_ticket_count > 0 THEN 15 ELSE 0 END
          + CASE WHEN customer_value_segment IN ('high_value', 'established_value') THEN 10 ELSE 0 END
          + CASE WHEN complaint_frequency >= 0.50 THEN 5 ELSE 0 END AS risk_score
    FROM vw_churn_customer_analytics
    WHERE churn_label = 0
),
ranked_high_risk AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY risk_score DESC, monthly_charges DESC) AS risk_rank,
        COUNT(*) OVER () AS retained_customer_count,
        monthly_charges * (risk_score / 100.0) AS monthly_revenue_at_risk
    FROM retained_customers
    WHERE risk_score >= 70
),
scenario_membership AS (
    SELECT
        *,
        CASE
            WHEN risk_rank <= CEIL(retained_customer_count * 0.05) THEN 1 ELSE 0
        END AS in_top_5_pct,
        CASE
            WHEN risk_rank <= CEIL(retained_customer_count * 0.10) THEN 1 ELSE 0
        END AS in_top_10_pct,
        CASE
            WHEN risk_rank <= CEIL(retained_customer_count * 0.20) THEN 1 ELSE 0
        END AS in_top_20_pct
    FROM ranked_high_risk
),
scenario_rows AS (
    SELECT 'Scenario A - top 5 pct high risk' AS scenario_name, * FROM scenario_membership WHERE in_top_5_pct = 1
    UNION ALL
    SELECT 'Scenario B - top 10 pct high risk' AS scenario_name, * FROM scenario_membership WHERE in_top_10_pct = 1
    UNION ALL
    SELECT 'Scenario C - top 20 pct high risk' AS scenario_name, * FROM scenario_membership WHERE in_top_20_pct = 1
)
SELECT
    scenario_name,
    COUNT(*) AS customers_targeted,
    ROUND(SUM(monthly_revenue_at_risk), 2) AS monthly_revenue_at_risk_targeted,
    ROUND(SUM(monthly_revenue_at_risk * 0.25), 2) AS estimated_monthly_revenue_saved,
    ROUND(SUM(monthly_revenue_at_risk * 0.25 * 12), 2) AS annualized_revenue_saved,
    ROUND(AVG(risk_score), 2) AS avg_risk_score,
    ROUND(SUM(estimated_customer_lifetime_value * (risk_score / 100.0)), 2) AS clv_at_risk_targeted
FROM scenario_rows
GROUP BY scenario_name
ORDER BY scenario_name;
