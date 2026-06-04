/*
Business purpose:
Create a stakeholder-friendly semantic view over churn_features_master.

Assumption:
The physical table `churn_features_master` already exists in the warehouse and
contains one row per unified_customer_id.
*/

CREATE OR REPLACE VIEW vw_churn_customer_analytics AS
WITH base AS (
    SELECT
        unified_customer_id,
        churn_label,
        senior_citizen,
        tenure,
        monthly_charges,
        total_charges_imputed,
        avg_monthly_spend,
        estimated_customer_lifetime_value,
        monthly_charge_to_tenure_ratio,
        payment_risk_score,
        engagement_score,
        support_burden_score,
        customer_health_score,
        inactivity_days,
        invoice_count,
        activity_line_count,
        net_activity_revenue,
        gross_activity_revenue,
        support_ticket_count,
        open_ticket_count,
        critical_ticket_count,
        low_satisfaction_ticket_count,
        complaint_ticket_count,
        complaint_frequency,
        avg_satisfaction_rating,
        is_month_to_month_contract,
        is_electronic_check,
        no_tech_support_flag,
        no_online_security_flag,
        no_activity_flag,
        has_activity_flag,
        has_support_flag,

        CASE
            WHEN contract_month_to_month = 1 THEN 'month_to_month'
            WHEN contract_one_year = 1 THEN 'one_year'
            WHEN contract_two_year = 1 THEN 'two_year'
            ELSE 'unknown'
        END AS contract_type,

        CASE
            WHEN payment_method_electronic_check = 1 THEN 'electronic_check'
            WHEN payment_method_mailed_check = 1 THEN 'mailed_check'
            WHEN payment_method_bank_transfer_automatic = 1 THEN 'bank_transfer_automatic'
            WHEN payment_method_credit_card_automatic = 1 THEN 'credit_card_automatic'
            ELSE 'unknown'
        END AS payment_method_type,

        CASE
            WHEN internet_service_fiber_optic = 1 THEN 'fiber_optic'
            WHEN internet_service_dsl = 1 THEN 'dsl'
            WHEN internet_service_no = 1 THEN 'no_internet_service'
            ELSE 'unknown'
        END AS internet_service_type,

        CASE
            WHEN customer_value_segment_high_value = 1 THEN 'high_value'
            WHEN customer_value_segment_established_value = 1 THEN 'established_value'
            WHEN customer_value_segment_emerging_value = 1 THEN 'emerging_value'
            WHEN customer_value_segment_low_value = 1 THEN 'low_value'
            ELSE 'unknown'
        END AS customer_value_segment,

        CASE
            WHEN tenure_segment_0_6_months = 1 THEN '0_6_months'
            WHEN tenure_segment_7_12_months = 1 THEN '7_12_months'
            WHEN tenure_segment_13_24_months = 1 THEN '13_24_months'
            WHEN tenure_segment_25_48_months = 1 THEN '25_48_months'
            WHEN tenure_segment_49_plus_months = 1 THEN '49_plus_months'
            ELSE 'unknown'
        END AS tenure_segment,

        CASE
            WHEN activity_status_active_0_30_days = 1 THEN 'active_0_30_days'
            WHEN activity_status_active_31_90_days = 1 THEN 'active_31_90_days'
            WHEN activity_status_inactive_90_plus_days = 1 THEN 'inactive_90_plus_days'
            WHEN activity_status_no_activity = 1 THEN 'no_activity'
            ELSE 'unknown'
        END AS activity_status
    FROM churn_features_master
),
scored AS (
    SELECT
        *,
        monthly_charges * churn_label AS realized_monthly_revenue_lost,
        estimated_customer_lifetime_value * churn_label AS realized_clv_lost,
        CASE
            WHEN payment_risk_score >= 0.70
              OR is_electronic_check = 1
              OR is_month_to_month_contract = 1
            THEN 'high_payment_risk'
            WHEN payment_risk_score >= 0.35 THEN 'medium_payment_risk'
            ELSE 'low_payment_risk'
        END AS payment_risk_segment,
        CASE
            WHEN engagement_score < 0.30 OR no_activity_flag = 1 THEN 'low_engagement'
            WHEN engagement_score < 0.60 THEN 'moderate_engagement'
            ELSE 'high_engagement'
        END AS engagement_segment,
        CASE
            WHEN support_burden_score >= 0.45
              OR open_ticket_count > 0
              OR critical_ticket_count > 0
              OR low_satisfaction_ticket_count > 0
            THEN 'high_support_burden'
            WHEN support_ticket_count > 0 THEN 'moderate_support_burden'
            ELSE 'low_support_burden'
        END AS support_burden_segment,
        CASE
            WHEN customer_health_score < 0.35 THEN 'weak_health'
            WHEN customer_health_score < 0.60 THEN 'moderate_health'
            ELSE 'strong_health'
        END AS customer_health_segment
    FROM base
)
SELECT *
FROM scored;
