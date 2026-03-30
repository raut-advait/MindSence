"""Train 4-level severity model from merged_training_v1.csv.

Usage:
    python scripts/train_severity_model.py

Expected input:
    data/processed/merged_training_v1.csv

Outputs saved to models/:
    - severity_preprocessor.pkl
    - severity_model.pkl
    - severity_features.json
    - severity_metadata.json
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
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


NUMERIC_FEATURES = [
    "Age",
    "CGPA",
    "Sleep_Duration",
    "Physical_Activity",
    "Stress_Level",
    "Anxiety_Score",
    "Social_Support",
    "Financial_Stress",
    "Sleep_Quality",
    "Diet_Quality",
    "Counseling_Service_Use",
    "Family_History",
]

CATEGORICAL_FEATURES = [
    "Gender",
    "Department",
]

TARGET_COLUMN = "Severity_Level"



def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )



def build_candidates(random_state: int) -> dict:
    return {
        "logistic": LogisticRegression(
            max_iter=1500,
            class_weight="balanced",
            random_state=random_state,
        ),
        "lightgbm": LGBMClassifier(
            objective="multiclass",
            num_class=4,
            class_weight="balanced",
            n_estimators=320,
            learning_rate=0.05,
            num_leaves=31,
            random_state=random_state,
            verbose=-1,
        ),
        "xgboost": XGBClassifier(
            objective="multi:softprob",
            num_class=4,
            n_estimators=260,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="mlogloss",
            random_state=random_state,
        ),
    }



def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    input_path = project_root / "data" / "processed" / "merged_training_v1.csv"
    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(
            "Missing merged dataset. Run scripts/build_merged_dataset.py first."
        )

    random_state = 42
    df = pd.read_csv(input_path)

    required = [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES, TARGET_COLUMN]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Merged dataset missing required columns: {missing}")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()
    y = pd.to_numeric(df[TARGET_COLUMN], errors="coerce").astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=random_state,
        stratify=y,
    )

    candidates = build_candidates(random_state)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=random_state)
    scoring = {
        "f1_macro": "f1_macro",
        "recall_macro": "recall_macro",
        "precision_macro": "precision_macro",
        "accuracy": "accuracy",
    }

    best_name = None
    best_metrics = None

    print("[severity-model] evaluating candidates")
    for name, estimator in candidates.items():
        pipeline = Pipeline([
            ("pre", build_preprocessor()),
            ("clf", estimator),
        ])

        cv_result = cross_validate(
            pipeline,
            X_train,
            y_train,
            cv=cv,
            scoring=scoring,
            return_train_score=False,
        )
        metrics = {
            "cv_f1_macro": float(np.mean(cv_result["test_f1_macro"])),
            "cv_recall_macro": float(np.mean(cv_result["test_recall_macro"])),
            "cv_precision_macro": float(np.mean(cv_result["test_precision_macro"])),
            "cv_accuracy": float(np.mean(cv_result["test_accuracy"])),
        }

        print(
            f"  {name:<10} f1_macro={metrics['cv_f1_macro']:.4f} "
            f"recall_macro={metrics['cv_recall_macro']:.4f} "
            f"acc={metrics['cv_accuracy']:.4f}"
        )

        if best_metrics is None or metrics["cv_f1_macro"] > best_metrics["cv_f1_macro"]:
            best_name = name
            best_metrics = metrics

    final_pipeline = Pipeline([
        ("pre", build_preprocessor()),
        ("clf", candidates[best_name]),
    ])
    final_pipeline.fit(X_train, y_train)

    y_pred = final_pipeline.predict(X_test)
    y_prob = final_pipeline.predict_proba(X_test)

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

    # Quality gate to avoid persisting unusable models.
    if test_metrics["f1_macro"] < 0.35 or test_metrics["accuracy"] < 0.45:
        print("\n[quality gate] FAILED - severity artifacts were not updated")
        raise SystemExit(1)

    preprocessor = final_pipeline.named_steps["pre"]
    classifier = final_pipeline.named_steps["clf"]

    joblib.dump(preprocessor, models_dir / "severity_preprocessor.pkl")
    joblib.dump(classifier, models_dir / "severity_model.pkl")

    with open(models_dir / "severity_features.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "numeric_features": NUMERIC_FEATURES,
                "categorical_features": CATEGORICAL_FEATURES,
                "target": TARGET_COLUMN,
            },
            fh,
            indent=2,
        )

    with open(models_dir / "severity_metadata.json", "w", encoding="utf-8") as fh:
        json.dump(
            {
                "model_name": "severity_model.pkl",
                "model_type": best_name,
                "task": "multiclass_severity_4level",
                "dataset": str(input_path.relative_to(project_root)),
                "training_date": datetime.now().isoformat(),
                "training_metrics": best_metrics,
                "test_metrics": test_metrics,
            },
            fh,
            indent=2,
        )

    print("\n[severity-model] selected:", best_name)
    print("[severity-model] artifacts saved in models/")


if __name__ == "__main__":
    main()
