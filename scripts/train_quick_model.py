"""Train quick-check-in severity model using quick-assessment fields.

Usage:
    python scripts/train_quick_model.py

Outputs saved to models/:
    - quick_preprocessor.pkl
    - quick_model.pkl
    - quick_features.json
    - quick_metadata.json
"""

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier


def build_preprocessor(numeric_features, categorical_features):
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ],
        remainder="drop",
    )


def clean_severity_quick_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    required = [
        "Sleep_Duration",
        "Study_Hours",
        "Social_Media",
        "Physical_Activity",
        "Stress_Level",
        "Age",
        "CGPA",
        "Gender",
        "Department",
        "Severity_Level",
    ]

    for col in ["Sleep_Duration", "Study_Hours", "Social_Media", "Physical_Activity", "Stress_Level", "Age", "CGPA"]:
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    cleaned["Sleep_Duration"] = cleaned["Sleep_Duration"].clip(2.0, 12.0)
    cleaned["Study_Hours"] = cleaned["Study_Hours"].clip(0.0, 12.0)
    cleaned["Social_Media"] = cleaned["Social_Media"].clip(0.0, 12.0)
    cleaned["Physical_Activity"] = cleaned["Physical_Activity"].clip(0.0, 6.0)
    cleaned["Stress_Level"] = cleaned["Stress_Level"].clip(0.0, 5.0)
    cleaned["Age"] = cleaned["Age"].clip(16.0, 40.0)
    cleaned["CGPA"] = cleaned["CGPA"].clip(0.0, 10.0)
    cleaned["Gender"] = cleaned["Gender"].fillna("Unknown").astype(str)
    cleaned["Department"] = cleaned["Department"].fillna("General").astype(str)

    cleaned = cleaned.dropna(subset=required).copy()
    cleaned["Severity_Level"] = pd.to_numeric(cleaned["Severity_Level"], errors="coerce").astype(int)
    return cleaned


def snap_to_options(value: float, options: np.ndarray) -> float:
    idx = int(np.argmin(np.abs(options - float(value))))
    return float(options[idx])


def main():
    project_root = Path(__file__).resolve().parent.parent
    data_path = project_root / "data" / "processed" / "merged_training_v1.csv"
    models_dir = project_root / "models"
    models_dir.mkdir(exist_ok=True)

    random_state = 42
    numeric_base_features = [
        "Sleep_Duration",
        "Study_Hours",
        "Social_Media",
        "Physical_Activity",
        "Stress_Level",
        "Age",
        "CGPA",
    ]
    categorical_features = ["Gender", "Department"]
    quick_features = [
        *numeric_base_features,
        *categorical_features,
        "sleep_study_ratio",
        "stress_x_sleep",
        "study_x_stress",
        "activity_social_balance",
    ]

    if not data_path.exists():
        raise FileNotFoundError("Missing merged severity dataset. Run scripts/build_merged_dataset.py first.")

    df = pd.read_csv(data_path)
    df = clean_severity_quick_dataframe(df)

    # Match training manifold to the exact options available in the quick UI.
    sleep_opts = np.array([2.0, 5.0, 7.0, 9.0])
    study_opts = np.array([1.0, 3.0, 5.0, 7.0])
    social_opts = np.array([0.5, 2.0, 4.0, 6.0])
    activity_opts = np.array([0.5, 1.5, 2.5, 3.5])

    df["Sleep_Duration"] = df["Sleep_Duration"].apply(lambda x: snap_to_options(x, sleep_opts))
    df["Study_Hours"] = df["Study_Hours"].apply(lambda x: snap_to_options(x, study_opts))
    df["Social_Media"] = df["Social_Media"].apply(lambda x: snap_to_options(x, social_opts))
    df["Physical_Activity"] = df["Physical_Activity"].apply(lambda x: snap_to_options(x, activity_opts))
    df["Stress_Level"] = np.rint(df["Stress_Level"]).clip(1, 5).astype(int)

    # Feature engineering that can be reproduced at inference from quick inputs.
    df["sleep_study_ratio"] = df["Sleep_Duration"] / (df["Study_Hours"] + 1.0)
    df["stress_x_sleep"] = df["Stress_Level"] * df["Sleep_Duration"]
    df["study_x_stress"] = df["Study_Hours"] * df["Stress_Level"]
    df["activity_social_balance"] = df["Physical_Activity"] - 0.5 * df["Social_Media"]

    X = df[quick_features].copy()
    numeric_quick_features = numeric_base_features + [
        "sleep_study_ratio",
        "stress_x_sleep",
        "study_x_stress",
        "activity_social_balance",
    ]
    for col in numeric_quick_features:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    y = df["Severity_Level"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    candidates = {
        "logistic": LogisticRegression(class_weight="balanced", max_iter=1000, random_state=random_state),
        "xgboost": XGBClassifier(
            objective="multi:softprob",
            num_class=4,
            n_estimators=220,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="mlogloss",
            random_state=random_state,
        ),
        "lightgbm": LGBMClassifier(
            objective="multiclass",
            num_class=4,
            class_weight="balanced",
            n_estimators=260,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.85,
            random_state=random_state,
            verbose=-1,
        ),
    }

    scoring = {
        "f1_macro": "f1_macro",
        "precision_macro": "precision_macro",
        "recall_macro": "recall_macro",
        "accuracy": "accuracy",
    }
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=random_state)

    best_name = None
    best_cv = None
    metrics_by_model = {}

    print("[quick-model] evaluating candidates")
    for model_name, estimator in candidates.items():
        preprocessor = build_preprocessor(numeric_base_features + ["sleep_study_ratio", "stress_x_sleep", "study_x_stress", "activity_social_balance"], categorical_features)
        pipe = Pipeline([("pre", preprocessor), ("clf", estimator)])
        res = cross_validate(pipe, X_train, y_train, cv=cv, scoring=scoring, return_train_score=False)
        cv_metrics = {
            "cv_f1_macro": float(np.mean(res["test_f1_macro"])),
            "cv_precision_macro": float(np.mean(res["test_precision_macro"])),
            "cv_recall_macro": float(np.mean(res["test_recall_macro"])),
            "cv_accuracy": float(np.mean(res["test_accuracy"])),
        }
        metrics_by_model[model_name] = cv_metrics
        print(
            f"  {model_name:<18} f1_macro={cv_metrics['cv_f1_macro']:.4f} "
            f"precision_macro={cv_metrics['cv_precision_macro']:.4f} "
            f"recall_macro={cv_metrics['cv_recall_macro']:.4f} acc={cv_metrics['cv_accuracy']:.4f}"
        )

        if best_cv is None or cv_metrics["cv_f1_macro"] > best_cv["cv_f1_macro"]:
            best_name = model_name
            best_cv = cv_metrics

    preprocessor = build_preprocessor(
        numeric_base_features + ["sleep_study_ratio", "stress_x_sleep", "study_x_stress", "activity_social_balance"],
        categorical_features,
    )
    final_pipe = Pipeline([
        ("pre", preprocessor),
        ("clf", candidates[best_name]),
    ])
    final_pipe.fit(X_train, y_train)

    y_pred = final_pipe.predict(X_test)
    y_prob = final_pipe.predict_proba(X_test)

    test_metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision_macro": float(precision_score(y_test, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_test, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
        "roc_auc_ovr": float(roc_auc_score(y_test, y_prob, multi_class="ovr", average="macro")),
    }

    print("\n[test metrics]")
    print(test_metrics)
    print("[classification report]")
    print(classification_report(y_test, y_pred, zero_division=0))
    print("[confusion matrix]")
    print(confusion_matrix(y_test, y_pred))

    if test_metrics["f1_macro"] < 0.35 or test_metrics["accuracy"] < 0.45:
        print("\n[quality gate] FAILED — artifacts were not updated")
        raise SystemExit(1)

    # Save preprocessor and classifier separately for app-side transform + predict_proba.
    joblib.dump(final_pipe.named_steps["pre"], models_dir / "quick_preprocessor.pkl")
    joblib.dump(final_pipe.named_steps["clf"], models_dir / "quick_model.pkl")

    with open(models_dir / "quick_features.json", "w", encoding="utf-8") as fh:
        json.dump({"quick_features": quick_features}, fh, indent=2)

    metadata = {
        "model_name": "quick_model.pkl",
        "model_type": best_name,
        "task": "multiclass_quick_severity_4level",
        "calibrated": False,
        "dataset_name": data_path.name,
        "dataset_size": int(len(df)),
        "selected_threshold": None,
        "class_labels": {
            "0": "Excellent Mental Well-being",
            "1": "Moderate Stress Detected",
            "2": "High Stress & Anxiety",
            "3": "Severe Distress Detected",
        },
        "training_date": datetime.now().isoformat(),
        "training_metrics": best_cv,
        "test_metrics": test_metrics,
    }
    with open(models_dir / "quick_metadata.json", "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    print("\n[quick-model] selected", best_name)
    print("[quick-model] test metrics:", test_metrics)
    print("[quick-model] artifacts saved to models/")


if __name__ == "__main__":
    main()
