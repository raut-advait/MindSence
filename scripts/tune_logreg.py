"""Hyperparameter tuning for LogisticRegression using GridSearchCV.

Usage:
    python scripts/tune_logreg.py --csv "data/Student Mental health.csv"

Saves best model to `models/logistic_model.pkl`, `models/scaler.pkl`, and updates `models/features.json`.
"""
import os
import json
import pandas as pd
import joblib
import numpy as np

from sklearn.model_selection import StratifiedKFold, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import make_scorer, f1_score


def preprocess(df):
    def map_yes_no(val):
        if pd.isna(val):
            return 0
        s = str(val).strip().lower()
        if s in ('yes','y','true','1'):
            return 1
        if s in ('no','n','false','0'):
            return 0
        if 'yes' in s:
            return 1
        if 'no' in s:
            return 0
        return 0

    def map_gender(val):
        if pd.isna(val):
            return 0
        s = str(val).strip().lower()
        if 'female' in s:
            return 1
        if 'male' in s:
            return 0
        return 2

    features = {}
    if 'Age' in df.columns:
        features['age'] = pd.to_numeric(df['Age'], errors='coerce').fillna(df['Age'].median())
    if 'Choose your gender' in df.columns:
        features['gender'] = df['Choose your gender'].map(map_gender)
    if 'What is your CGPA?' in df.columns:
        features['cgpa'] = pd.to_numeric(df['What is your CGPA?'].astype(str).str.replace('[^0-9\.]','', regex=True), errors='coerce')
        features['cgpa'] = features['cgpa'].fillna(features['cgpa'].median())
    if 'Your current year of Study' in df.columns:
        ycol = df['Your current year of Study'].astype(str).str.extract(r'(\d+)')
        if ycol.notna().any().any():
            features['year'] = pd.to_numeric(ycol[0], errors='coerce').fillna(0)
    if 'What is your course?' in df.columns:
        features['course'] = pd.factorize(df['What is your course?'].fillna('unknown'))[0]

    yesno_cols = {
        'Do you have Depression?': 'depression',
        'Do you have Anxiety?': 'anxiety',
        'Do you have Panic attack?': 'panic',
        'Did you seek any specialist for a treatment?': 'sought_treatment'
    }
    for col, name in yesno_cols.items():
        if col in df.columns:
            features[name] = df[col].map(map_yes_no)

    if not features:
        numeric = df.select_dtypes(include=['int64','float64']).columns.tolist()
        if not numeric:
            raise SystemExit('No usable features found')
        X = df[numeric].fillna(0)
    else:
        X = pd.DataFrame(features).fillna(0)

    medians = {k: float(v) for k, v in X.median().to_dict().items()}
    y = X.sum(axis=1)
    y = (y > y.median()).astype(int)
    return X, y, medians


def main(csv_path):
    if not os.path.exists(csv_path):
        raise SystemExit('CSV not found: ' + csv_path)
    df = pd.read_csv(csv_path)
    X, y, medians = preprocess(df)

    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', LogisticRegression(max_iter=2000))
    ])

    param_grid = {
        'clf__penalty': ['l2', 'none'],
        'clf__C': [0.01, 0.1, 1, 10, 100],
        'clf__solver': ['lbfgs', 'saga']
    }

    # For small datasets use StratifiedKFold
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scorer = make_scorer(f1_score)

    gs = GridSearchCV(pipe, param_grid, cv=skf, scoring=scorer, n_jobs=-1, verbose=1)
    gs.fit(X, y)

    print('Best params:', gs.best_params_)
    print('Best CV F1:', gs.best_score_)

    # Save best estimator's classifier and scaler separately for app compatibility
    best_pipe = gs.best_estimator_
    scaler = best_pipe.named_steps['scaler']
    clf = best_pipe.named_steps['clf']
    os.makedirs('models', exist_ok=True)
    joblib.dump(clf, 'models/logistic_model.pkl')
    joblib.dump(scaler, 'models/scaler.pkl')
    with open('models/features.json', 'w', encoding='utf-8') as f:
        json.dump({'feature_names': X.columns.tolist(), 'medians': medians}, f, indent=2)

    print('Saved tuned model and metadata to models/')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    args = p.parse_args()
    main(args.csv)
