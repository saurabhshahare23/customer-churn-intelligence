"""Train and evaluate churn prediction models.

This workflow loads the ML-ready feature table, performs a stratified train-test
split, trains multiple imbalance-aware models, evaluates classification quality,
saves model artifacts, creates diagnostics, and writes a business interpretation
report. Optional libraries such as XGBoost, LightGBM, and SHAP are used when
available.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURE_PATH = PROJECT_ROOT / "data" / "processed" / "churn_features_master.csv"
TRAINED_MODELS_DIR = PROJECT_ROOT / "models" / "trained_models"
MODEL_METRICS_DIR = PROJECT_ROOT / "models" / "model_metrics"
FEATURE_IMPORTANCE_DIR = PROJECT_ROOT / "models" / "feature_importance"
FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"
REPORTS_DIR = PROJECT_ROOT / "reports" / "business_reports"

TARGET_COLUMN = "churn_label"
ID_COLUMN = "unified_customer_id"
RANDOM_STATE = 42
TEST_SIZE = 0.20


def ensure_output_dirs() -> None:
    """Create output directories used by the modeling workflow."""
    for path in [TRAINED_MODELS_DIR, MODEL_METRICS_DIR, FEATURE_IMPORTANCE_DIR, FIGURES_DIR, REPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def dataframe_to_markdown(df: pd.DataFrame, max_rows: int = 20) -> str:
    """Render a dataframe as Markdown without optional dependencies."""
    render_df = df.head(max_rows).copy().fillna("").astype(str)
    headers = list(render_df.columns)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in render_df.values.tolist():
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def load_feature_dataset() -> pd.DataFrame:
    """Load the final ML-ready churn feature dataset."""
    df = pd.read_csv(FEATURE_PATH)
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Expected target column '{TARGET_COLUMN}' in {FEATURE_PATH}")
    if ID_COLUMN not in df.columns:
        raise ValueError(f"Expected identifier column '{ID_COLUMN}' in {FEATURE_PATH}")
    return df


def prepare_model_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series, List[str]]:
    """Separate identifier, target, and numeric model features."""
    customer_ids = df[ID_COLUMN].copy()
    y = df[TARGET_COLUMN].astype(int)
    leakage_columns = [ID_COLUMN, TARGET_COLUMN]
    X = df.drop(columns=leakage_columns).copy()

    non_numeric_columns = X.select_dtypes(exclude=["number", "bool"]).columns.tolist()
    if non_numeric_columns:
        X = X.drop(columns=non_numeric_columns)

    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    return X, y, customer_ids, non_numeric_columns


def class_balance_summary(y: pd.Series) -> pd.DataFrame:
    """Summarize target distribution and imbalance ratio."""
    counts = y.value_counts().sort_index()
    total = len(y)
    rows = []
    for label, count in counts.items():
        rows.append(
            {
                "churn_label": int(label),
                "customer_count": int(count),
                "customer_pct": round(count / total * 100, 2),
            }
        )
    minority = counts.min()
    majority = counts.max()
    rows.append(
        {
            "churn_label": "imbalance_ratio_majority_to_minority",
            "customer_count": round(float(majority / minority), 4),
            "customer_pct": "",
        }
    )
    return pd.DataFrame(rows)


def build_candidate_models(y_train: pd.Series) -> Tuple[Dict[str, object], List[Dict[str, str]]]:
    """Build required and optional candidate classifiers."""
    negative_count = int((y_train == 0).sum())
    positive_count = int((y_train == 1).sum())
    scale_pos_weight = negative_count / positive_count

    models: Dict[str, object] = {
        "logistic_regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        solver="liblinear",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=None,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            n_jobs=1,
            random_state=RANDOM_STATE,
        ),
    }

    skipped = []

    try:
        from xgboost import XGBClassifier

        models["xgboost"] = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
            random_state=RANDOM_STATE,
        )
    except Exception as exc:
        skipped.append(
            {
                "component": "xgboost",
                "reason": f"XGBoost is not available in this environment: {exc}",
            }
        )

    try:
        from lightgbm import LGBMClassifier

        models["lightgbm"] = LGBMClassifier(
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        )
    except Exception as exc:
        skipped.append(
            {
                "component": "lightgbm",
                "reason": f"LightGBM is not available in this environment: {exc}",
            }
        )

    return models, skipped


def predict_positive_probability(model: object, X: pd.DataFrame) -> np.ndarray:
    """Return churn probabilities for classifiers with probability support."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    if hasattr(model, "decision_function"):
        scores = model.decision_function(X)
        return 1 / (1 + np.exp(-scores))
    raise ValueError("Model does not expose predict_proba or decision_function.")


def evaluate_model(model_name: str, model: object, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
    """Evaluate a trained classifier using standard churn metrics."""
    y_pred = model.predict(X_test)
    y_proba = predict_positive_probability(model, X_test)
    return {
        "model_name": model_name,
        "accuracy": round(accuracy_score(y_test, y_pred), 6),
        "precision": round(precision_score(y_test, y_pred, zero_division=0), 6),
        "recall": round(recall_score(y_test, y_pred, zero_division=0), 6),
        "f1_score": round(f1_score(y_test, y_pred, zero_division=0), 6),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 6),
    }


def plot_confusion_matrix(model_name: str, y_test: pd.Series, y_pred: np.ndarray) -> Path:
    """Save confusion matrix heatmap for a model."""
    matrix = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Predicted retained", "Predicted churn"],
        yticklabels=["Actual retained", "Actual churn"],
    )
    plt.title(f"Confusion Matrix - {model_name.replace('_', ' ').title()}")
    plt.xlabel("Predicted label")
    plt.ylabel("Actual label")
    plt.tight_layout()
    output_path = FIGURES_DIR / f"confusion_matrix_{model_name}.png"
    plt.savefig(output_path, dpi=160)
    plt.close()
    return output_path


def plot_roc_curves(
    trained_models: Dict[str, object],
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Path:
    """Save combined ROC curve plot for all trained models."""
    plt.figure(figsize=(8, 6))
    for model_name, model in trained_models.items():
        y_proba = predict_positive_probability(model, X_test)
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        auc_value = roc_auc_score(y_test, y_proba)
        plt.plot(fpr, tpr, label=f"{model_name.replace('_', ' ').title()} AUC={auc_value:.3f}")

    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Random baseline")
    plt.title("ROC Curves - Churn Prediction Models")
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.legend(loc="lower right")
    plt.tight_layout()
    output_path = FIGURES_DIR / "roc_curves_churn_models.png"
    plt.savefig(output_path, dpi=160)
    plt.close()
    return output_path


def extract_model_importance(
    model_name: str,
    model: object,
    feature_names: List[str],
) -> pd.DataFrame:
    """Extract native model importance where available."""
    estimator = model
    if isinstance(model, Pipeline):
        estimator = model.named_steps["model"]

    if hasattr(estimator, "feature_importances_"):
        values = estimator.feature_importances_
        importance_type = "native_feature_importance"
    elif hasattr(estimator, "coef_"):
        values = np.abs(estimator.coef_[0])
        importance_type = "absolute_logistic_coefficient"
    else:
        return pd.DataFrame(columns=["model_name", "feature", "importance", "importance_type"])

    importance = pd.DataFrame(
        {
            "model_name": model_name,
            "feature": feature_names,
            "importance": values,
            "importance_type": importance_type,
        }
    )
    return importance.sort_values("importance", ascending=False).reset_index(drop=True)


def plot_feature_importance(importance: pd.DataFrame, model_name: str, file_suffix: str) -> Path:
    """Save top feature importance chart."""
    top = importance.head(20).sort_values("importance", ascending=True)
    plt.figure(figsize=(10, 8))
    sns.barplot(data=top, x="importance", y="feature", color="#3A7D7C")
    plt.title(f"Top Churn Drivers - {model_name.replace('_', ' ').title()}")
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()
    output_path = FIGURES_DIR / f"feature_importance_{model_name}_{file_suffix}.png"
    plt.savefig(output_path, dpi=160)
    plt.close()
    return output_path


def build_permutation_importance(
    best_model_name: str,
    best_model: object,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> pd.DataFrame:
    """Create model-agnostic permutation importance for the best model."""
    result = permutation_importance(
        best_model,
        X_test,
        y_test,
        scoring="roc_auc",
        n_repeats=10,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    importance = pd.DataFrame(
        {
            "model_name": best_model_name,
            "feature": X_test.columns,
            "importance": result.importances_mean,
            "importance_std": result.importances_std,
            "importance_type": "permutation_importance_roc_auc",
        }
    )
    return importance.sort_values("importance", ascending=False).reset_index(drop=True)


def run_shap_explainability(
    best_model_name: str,
    best_model: object,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    """Run SHAP explainability when the optional shap package is installed."""
    skipped = []
    try:
        import shap
    except Exception as exc:
        skipped.append(
            {
                "component": "shap",
                "reason": f"SHAP is not available in this environment: {exc}",
            }
        )
        return pd.DataFrame(), skipped

    sample_train = X_train.sample(min(300, len(X_train)), random_state=RANDOM_STATE)
    sample_test = X_test.sample(min(500, len(X_test)), random_state=RANDOM_STATE)

    try:
        model_for_shap = best_model
        if isinstance(best_model, Pipeline):
            transformed_train = best_model.named_steps["scaler"].transform(sample_train)
            transformed_test = best_model.named_steps["scaler"].transform(sample_test)
            model_for_shap = best_model.named_steps["model"]
            explainer = shap.LinearExplainer(model_for_shap, transformed_train)
            shap_values = explainer.shap_values(transformed_test)
        else:
            explainer = shap.TreeExplainer(model_for_shap)
            shap_values = explainer.shap_values(sample_test)

        if isinstance(shap_values, list):
            shap_values = shap_values[-1]

        mean_abs = np.abs(shap_values).mean(axis=0)
        shap_importance = pd.DataFrame(
            {
                "model_name": best_model_name,
                "feature": X_test.columns,
                "mean_abs_shap_value": mean_abs,
            }
        ).sort_values("mean_abs_shap_value", ascending=False)

        shap_importance.to_csv(FEATURE_IMPORTANCE_DIR / "shap_feature_importance.csv", index=False)

        shap.summary_plot(
            shap_values,
            sample_test,
            show=False,
            max_display=20,
            plot_type="bar",
        )
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "shap_summary_best_model.png", dpi=160, bbox_inches="tight")
        plt.close()
        return shap_importance, skipped
    except Exception as exc:
        skipped.append(
            {
                "component": "shap",
                "reason": f"SHAP execution failed for {best_model_name}: {exc}",
            }
        )
        return pd.DataFrame(), skipped


def business_meaning(feature: str) -> str:
    """Map important engineered features to business interpretation."""
    exact_map = {
        "payment_risk_score": "Payment and contract setup suggests elevated churn exposure.",
        "monthly_charge_to_tenure_ratio": "High charges relative to tenure can indicate early value pressure.",
        "is_month_to_month_contract": "Flexible contract customers can leave more easily.",
        "customer_health_score": "Composite health indicator across engagement, support, payment risk, and tenure.",
        "tenure": "Shorter customer tenure often reflects weaker adoption and relationship depth.",
        "no_tech_support_flag": "Lack of technical support can reduce perceived service value.",
        "no_online_security_flag": "Missing security add-ons may reflect lower product stickiness.",
        "engagement_score": "Lower activity engagement may signal fading usage or interest.",
        "support_burden_score": "Higher operational friction may indicate customer frustration.",
        "complaint_frequency": "Frequent complaint-related tickets can precede churn.",
        "inactivity_days": "More days since activity can signal disengagement.",
    }
    if feature in exact_map:
        return exact_map[feature]
    if "contract_month_to_month" in feature:
        return "Month-to-month contracts are easier to cancel than annual commitments."
    if "fiber_optic" in feature:
        return "Internet service type can reflect different price, experience, or support patterns."
    if "electronic_check" in feature:
        return "Electronic check customers historically show higher churn in this dataset."
    if "tenure_segment" in feature:
        return "Tenure bands capture customer lifecycle maturity."
    if "online_security" in feature or "tech_support" in feature:
        return "Add-on services can be proxies for product stickiness and support coverage."
    if "monthly_charges" in feature:
        return "Monthly spend measures revenue exposure and price sensitivity."
    return "Feature contributes predictive signal and should be reviewed with domain stakeholders."


def write_model_report(
    metrics: pd.DataFrame,
    balance: pd.DataFrame,
    best_model_name: str,
    native_importance: pd.DataFrame,
    permutation: pd.DataFrame,
    skipped: List[Dict[str, str]],
    X_train_shape: Tuple[int, int],
    X_test_shape: Tuple[int, int],
) -> None:
    """Write a modeling and explainability report in Markdown."""
    top_drivers = permutation.head(15).copy()
    if top_drivers.empty:
        top_drivers = native_importance.head(15).copy()
    top_drivers["business_meaning"] = top_drivers["feature"].map(business_meaning)

    skipped_df = pd.DataFrame(skipped) if skipped else pd.DataFrame(columns=["component", "reason"])
    best_row = metrics.loc[metrics["model_name"].eq(best_model_name)].iloc[0]

    markdown = f"""# Churn Prediction Modeling Report

## Scope

This workflow trains churn prediction models using
`data/processed/churn_features_master.csv`. It focuses on modeling quality,
explainability, and business interpretation. No dashboards are created.

## Dataset Preparation

- Target: `churn_label`
- Identifier excluded from predictors: `unified_customer_id`
- Train/test split: stratified `{int((1 - TEST_SIZE) * 100)}/{int(TEST_SIZE * 100)}`
- Training matrix: `{X_train_shape[0]:,}` rows x `{X_train_shape[1]:,}` features
- Test matrix: `{X_test_shape[0]:,}` rows x `{X_test_shape[1]:,}` features
- Class imbalance handling: class-weighted Logistic Regression and Random Forest; optional gradient boosting uses class imbalance parameters when available.

## Class Balance

{dataframe_to_markdown(balance, max_rows=10)}

## Model Comparison

{dataframe_to_markdown(metrics, max_rows=20)}

The selected best model is **{best_model_name}**, chosen by highest ROC-AUC
with F1-score as the secondary consideration. Its test ROC-AUC is
**{best_row['roc_auc']}** and F1-score is **{best_row['f1_score']}**.

## Top Churn Drivers

{dataframe_to_markdown(top_drivers, max_rows=15)}

## Business Interpretation

- Features related to contract flexibility and payment risk indicate whether the customer can churn easily and whether their billing setup resembles historically higher-risk behavior.
- Tenure and customer health features capture lifecycle maturity. Early-tenure customers usually need stronger onboarding and value realization.
- Service add-ons such as technical support and online security can behave like product stickiness signals.
- Engagement, inactivity, and support burden features connect predictive patterns to operational actions: reactivation, support recovery, and targeted retention.

## Explainability Notes

Native model importances and model-agnostic permutation importance are saved.
SHAP outputs are generated automatically when the `shap` package is installed.

## Optional Components

{dataframe_to_markdown(skipped_df, max_rows=20)}

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
"""
    (REPORTS_DIR / "churn_modeling_report.md").write_text(markdown, encoding="utf-8")


def run_workflow() -> None:
    """Execute the full churn modeling workflow."""
    ensure_output_dirs()
    df = load_feature_dataset()
    X, y, customer_ids, dropped_non_numeric = prepare_model_matrix(df)
    balance = class_balance_summary(y)

    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X,
        y,
        customer_ids,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    candidate_models, skipped = build_candidate_models(y_train)
    trained_models: Dict[str, object] = {}
    metric_rows = []
    native_importance_frames = []

    for model_name, model in candidate_models.items():
        model.fit(X_train, y_train)
        trained_models[model_name] = model
        metric_rows.append(evaluate_model(model_name, model, X_test, y_test))

        y_pred = model.predict(X_test)
        plot_confusion_matrix(model_name, y_test, y_pred)

        importance = extract_model_importance(model_name, model, list(X_train.columns))
        if not importance.empty:
            native_importance_frames.append(importance)
            importance.to_csv(FEATURE_IMPORTANCE_DIR / f"{model_name}_feature_importance.csv", index=False)
            plot_feature_importance(importance, model_name, "native")

    metrics = pd.DataFrame(metric_rows).sort_values(["roc_auc", "f1_score"], ascending=False)
    best_model_name = metrics.iloc[0]["model_name"]
    best_model = trained_models[best_model_name]

    plot_roc_curves(trained_models, X_test, y_test)

    if native_importance_frames:
        native_importance = pd.concat(native_importance_frames, ignore_index=True)
    else:
        native_importance = pd.DataFrame(columns=["model_name", "feature", "importance", "importance_type"])

    best_native = native_importance.loc[native_importance["model_name"].eq(best_model_name)].copy()
    if not best_native.empty:
        plot_feature_importance(best_native, best_model_name, "best_native")

    permutation = build_permutation_importance(best_model_name, best_model, X_test, y_test)
    plot_feature_importance(
        permutation.rename(columns={"importance": "importance"}),
        best_model_name,
        "permutation",
    )

    shap_importance, shap_skipped = run_shap_explainability(best_model_name, best_model, X_train, X_test)
    skipped.extend(shap_skipped)
    if dropped_non_numeric:
        skipped.append(
            {
                "component": "non_numeric_feature_columns",
                "reason": "Dropped non-numeric predictor columns: " + ", ".join(dropped_non_numeric),
            }
        )

    model_package = {
        "best_model_name": best_model_name,
        "model": best_model,
        "feature_columns": list(X_train.columns),
        "target_column": TARGET_COLUMN,
        "id_column": ID_COLUMN,
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
    }

    joblib.dump(model_package, TRAINED_MODELS_DIR / "best_churn_model.joblib")
    joblib.dump(trained_models, TRAINED_MODELS_DIR / "all_trained_churn_models.joblib")

    metrics.to_csv(MODEL_METRICS_DIR / "model_comparison_metrics.csv", index=False)
    balance.to_csv(MODEL_METRICS_DIR / "class_balance_summary.csv", index=False)
    pd.DataFrame(skipped).to_csv(MODEL_METRICS_DIR / "skipped_optional_components.csv", index=False)
    native_importance.to_csv(FEATURE_IMPORTANCE_DIR / "model_feature_importance.csv", index=False)
    permutation.to_csv(FEATURE_IMPORTANCE_DIR / "permutation_importance_best_model.csv", index=False)

    predictions = pd.DataFrame(
        {
            ID_COLUMN: ids_test.values,
            "actual_churn_label": y_test.values,
            "predicted_churn_label": best_model.predict(X_test),
            "predicted_churn_probability": predict_positive_probability(best_model, X_test),
            "best_model_name": best_model_name,
        }
    )
    predictions.to_csv(MODEL_METRICS_DIR / "best_model_test_predictions.csv", index=False)

    metadata = {
        "best_model_name": best_model_name,
        "feature_count": int(X_train.shape[1]),
        "train_rows": int(X_train.shape[0]),
        "test_rows": int(X_test.shape[0]),
        "target_column": TARGET_COLUMN,
        "id_column": ID_COLUMN,
        "optional_components_skipped": skipped,
    }
    (MODEL_METRICS_DIR / "model_training_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    write_model_report(
        metrics,
        balance,
        best_model_name,
        best_native if not best_native.empty else permutation,
        permutation,
        skipped,
        X_train.shape,
        X_test.shape,
    )

    print("Churn modeling workflow complete.")
    print(f"Trained models: {', '.join(trained_models.keys())}")
    print(f"Best model: {best_model_name}")
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    run_workflow()
