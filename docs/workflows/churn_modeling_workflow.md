# Churn Prediction Modeling Workflow

## Purpose

This workflow trains and evaluates churn prediction models using the final
ML-ready dataset `data/processed/churn_features_master.csv`.

The focus is modeling quality, explainability, and business interpretation.
Dashboard development is intentionally out of scope.

## Inputs

- `data/processed/churn_features_master.csv`

## Outputs

### Trained Models

- `models/trained_models/best_churn_model.joblib`
- `models/trained_models/all_trained_churn_models.joblib`

### Metrics and Diagnostics

- `models/model_metrics/model_comparison_metrics.csv`
- `models/model_metrics/class_balance_summary.csv`
- `models/model_metrics/best_model_test_predictions.csv`
- `models/model_metrics/model_training_metadata.json`
- `models/model_metrics/skipped_optional_components.csv`

### Feature Importance

- `models/feature_importance/model_feature_importance.csv`
- `models/feature_importance/permutation_importance_best_model.csv`
- Per-model feature importance files where native importance is available

### Figures

- Confusion matrices in `reports/figures/`
- Combined ROC curve in `reports/figures/`
- Feature importance charts in `reports/figures/`
- SHAP summary chart when SHAP is installed

### Report

- `reports/business_reports/churn_modeling_report.md`

## Modeling Steps

1. Load the feature-engineered dataset.
2. Separate `unified_customer_id`, `churn_label`, and predictor features.
3. Drop non-numeric predictor columns if any remain.
4. Perform a stratified train-test split to preserve churn class balance.
5. Train imbalance-aware models:
   - Logistic Regression with `class_weight="balanced"`
   - Random Forest with `class_weight="balanced_subsample"`
   - XGBoost when the package is installed
   - LightGBM when the package is installed
6. Evaluate models with accuracy, precision, recall, F1-score, and ROC-AUC.
7. Save confusion matrices and ROC curves.
8. Create native feature importance and model-agnostic permutation importance.
9. Run SHAP explainability when the `shap` package is installed.
10. Save the best model package with feature columns and metadata.

## Best-Practice Notes

- The split is stratified because churn is imbalanced.
- The row identifier is retained for traceability but excluded from predictors.
- Class weights are used instead of resampling so the original customer
  distribution remains intact.
- ROC-AUC is used for primary model selection, with F1-score as a secondary
  criterion.
- The workflow records optional unavailable components instead of failing when
  packages are not installed.

## Run Command

From the project root:

```bash
python src/training/train_churn_models.py
```
