# Churn Prediction Modeling Report

## Scope

This workflow trains churn prediction models using
`data/processed/churn_features_master.csv`. It focuses on modeling quality,
explainability, and business interpretation. No dashboards are created.

## Dataset Preparation

- Target: `churn_label`
- Identifier excluded from predictors: `unified_customer_id`
- Train/test split: stratified `80/20`
- Training matrix: `5,634` rows x `195` features
- Test matrix: `1,409` rows x `195` features
- Class imbalance handling: class-weighted Logistic Regression and Random Forest; optional gradient boosting uses class imbalance parameters when available.

## Class Balance

| churn_label | customer_count | customer_pct |
| --- | --- | --- |
| 0 | 5174.0 | 73.46 |
| 1 | 1869.0 | 26.54 |
| imbalance_ratio_majority_to_minority | 2.7683 |  |

## Model Comparison

| model_name | accuracy | precision | recall | f1_score | roc_auc |
| --- | --- | --- | --- | --- | --- |
| logistic_regression | 0.750887 | 0.520211 | 0.791444 | 0.627784 | 0.841412 |
| random_forest | 0.789212 | 0.60105 | 0.612299 | 0.606623 | 0.840004 |

The selected best model is **logistic_regression**, chosen by highest ROC-AUC
with F1-score as the secondary consideration. Its test ROC-AUC is
**0.841412** and F1-score is **0.627784**.

## Top Churn Drivers

| model_name | feature | importance | importance_std | importance_type | business_meaning |
| --- | --- | --- | --- | --- | --- |
| logistic_regression | monthly_charges | 0.04359528791753855 | 0.006137476223514347 | permutation_importance_roc_auc | Monthly spend measures revenue exposure and price sensitivity. |
| logistic_regression | tenure | 0.03933581337673407 | 0.005479505596509103 | permutation_importance_roc_auc | Shorter customer tenure often reflects weaker adoption and relationship depth. |
| logistic_regression | net_activity_revenue | 0.02584334392518537 | 0.0027478490674987064 | permutation_importance_roc_auc | Feature contributes predictive signal and should be reviewed with domain stakeholders. |
| logistic_regression | gross_activity_revenue | 0.020088868221860588 | 0.003023289575628959 | permutation_importance_roc_auc | Feature contributes predictive signal and should be reviewed with domain stakeholders. |
| logistic_regression | internet_service_fiber_optic | 0.017445296959363466 | 0.003752242470861578 | permutation_importance_roc_auc | Internet service type can reflect different price, experience, or support patterns. |
| logistic_regression | monthly_charge_to_tenure_ratio | 0.011449275362318868 | 0.0024259436114441642 | permutation_importance_roc_auc | High charges relative to tenure can indicate early value pressure. |
| logistic_regression | internet_service_dsl | 0.011196104265157958 | 0.0019092182749934847 | permutation_importance_roc_auc | Feature contributes predictive signal and should be reviewed with domain stakeholders. |
| logistic_regression | customer_health_score | 0.00958381771681005 | 0.0029436117007157797 | permutation_importance_roc_auc | Composite health indicator across engagement, support, payment risk, and tenure. |
| logistic_regression | contract_two_year | 0.007889896406520469 | 0.003281203271986361 | permutation_importance_roc_auc | Feature contributes predictive signal and should be reviewed with domain stakeholders. |
| logistic_regression | streaming_movies_yes | 0.005060321888966412 | 0.0010180083656100318 | permutation_importance_roc_auc | Feature contributes predictive signal and should be reviewed with domain stakeholders. |
| logistic_regression | tenure_segment_0_6_months | 0.004937094732491187 | 0.001685207921128434 | permutation_importance_roc_auc | Tenure bands capture customer lifecycle maturity. |
| logistic_regression | is_month_to_month_contract | 0.004168797953964176 | 0.0019553220155969836 | permutation_importance_roc_auc | Flexible contract customers can leave more easily. |
| logistic_regression | contract_month_to_month | 0.004168797953964176 | 0.0019553220155969836 | permutation_importance_roc_auc | Month-to-month contracts are easier to cancel than annual commitments. |
| logistic_regression | streaming_tv_yes | 0.0034873026944638565 | 0.0018468307235518862 | permutation_importance_roc_auc | Feature contributes predictive signal and should be reviewed with domain stakeholders. |
| logistic_regression | complaint_ticket_count | 0.0033059495207833356 | 0.0015631459997175541 | permutation_importance_roc_auc | Feature contributes predictive signal and should be reviewed with domain stakeholders. |

## Business Interpretation

- Features related to contract flexibility and payment risk indicate whether the customer can churn easily and whether their billing setup resembles historically higher-risk behavior.
- Tenure and customer health features capture lifecycle maturity. Early-tenure customers usually need stronger onboarding and value realization.
- Service add-ons such as technical support and online security can behave like product stickiness signals.
- Engagement, inactivity, and support burden features connect predictive patterns to operational actions: reactivation, support recovery, and targeted retention.

## Explainability Notes

Native model importances and model-agnostic permutation importance are saved.
SHAP outputs are generated automatically when the `shap` package is installed.

## Optional Components

| component | reason |
| --- | --- |
| xgboost | XGBoost is not available in this environment: No module named 'xgboost' |
| lightgbm | LightGBM is not available in this environment: No module named 'lightgbm' |
| shap | SHAP is not available in this environment: No module named 'shap' |

## Saved Outputs

- `models/trained_models/best_churn_model.joblib`
- `models/trained_models/all_trained_churn_models.joblib`
- `models/model_metrics/model_comparison_metrics.csv`
- `models/model_metrics/class_balance_summary.csv`
- `models/model_metrics/skipped_optional_components.csv`
- `models/feature_importance/model_feature_importance.csv`
- `models/feature_importance/permutation_importance_best_model.csv`
- `reports/figures/confusion_matrix_*.png`
- `reports/figures/roc_curves_churn_models.png`
- `reports/figures/feature_importance_*.png`
