"""Evaluate saved lifestyle depression model on the original CSV.

Usage:
    python scripts/evaluate_lifestyle_model.py
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)


def load_data(path: Path):
    df = pd.read_csv(path)
    if "Student_ID" in df.columns:
        df = df.drop(columns=["Student_ID"])
    if "Social_Media_Hours" in df.columns:
        df = df.rename(columns={"Social_Media_Hours": "Social_Media"})
    df["Depression"] = df["Depression"].map({True: 1, False: 0, "True": 1, "False": 0})
    return df


def main():
    data_path = Path("data/student_lifestyle_100k.csv")
    models_dir = Path("models")

    print(f"[data] loading {data_path}")
    df = load_data(data_path)

    # load artifacts
    print(f"[models] loading preprocessor and classifier")
    pre = joblib.load(models_dir / "preprocessor.pkl")
    clf = joblib.load(models_dir / "trained_model.pkl")
    with open(models_dir / "metadata.json") as f:
        meta = json.load(f)
    thresh = meta.get("selected_threshold", 0.5)

    # feature list comes from features.json
    with open(models_dir / "features.json") as f:
        feat_meta = json.load(f)
    numeric = feat_meta.get("numeric_features", [])
    categorical = feat_meta.get("categorical_features", [])
    features = categorical + numeric

    X = df[features].copy()
    y = df["Depression"].astype(int)

    # predictions (pipeline already includes preprocessing)
    y_pred = clf.predict(X)
    y_prob = clf.predict_proba(X)[:, 1]
    y_thr = (y_prob >= thresh).astype(int)

    print(f"\n[eval] using threshold={thresh}")
    print(f"Accuracy : {accuracy_score(y, y_thr):.4f}")
    print(f"Precision: {precision_score(y, y_thr, zero_division=0):.4f}")
    print(f"Recall   : {recall_score(y, y_thr, zero_division=0):.4f}")
    print(f"F1       : {f1_score(y, y_thr, zero_division=0):.4f}")
    try:
        print(f"ROC-AUC  : {roc_auc_score(y, y_prob):.4f}")
    except Exception:
        pass
    print("Confusion matrix:\n", confusion_matrix(y, y_thr))
    print("Classification report:\n", classification_report(y, y_thr))


if __name__ == '__main__':
    main()
