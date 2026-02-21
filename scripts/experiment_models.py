"""Run simple experiments comparing several classifiers and save the best model.

This script reuses the preprocessing logic in `preprocess_and_train.py` to
construct features, then evaluates LogisticRegression, RandomForest,
GradientBoosting and XGBoost (if installed) using StratifiedKFold CV.
The best model by mean CV F1-score is saved to `models/logistic_model.pkl`
and the scaler and features metadata are saved alongside.
"""
import os
import json
import pandas as pd
import numpy as np
import joblib

from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.pipeline import make_pipeline
from sklearn.metrics import make_scorer, f1_score

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:
    HAS_XGB = False


def preprocess(df):
    # replicate preprocessing used earlier
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

    print('Features:', X.columns.tolist())

    models = {
        'logreg': LogisticRegression(max_iter=1000),
        'rf': RandomForestClassifier(random_state=42),
        'gb': GradientBoostingClassifier(random_state=42)
    }
    if HAS_XGB:
        models['xgb'] = XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scorer = make_scorer(f1_score)

    best_name = None
    best_score = -1
    best_model = None

    for name, clf in models.items():
        pipe = make_pipeline(StandardScaler(), clf)
        scores = cross_val_score(pipe, X, y, cv=skf, scoring=scorer)
        mean = float(np.mean(scores))
        std = float(np.std(scores))
        print(f"{name}: mean F1 = {mean:.3f} (+/- {std:.3f})")
        if mean > best_score:
            best_score = mean
            best_name = name
            best_model = pipe

    print('Best model:', best_name, 'CV F1:', best_score)

    # Fit best model on full data and save
    best_model.fit(X, y)
    os.makedirs('models', exist_ok=True)
    joblib.dump(best_model.named_steps[list(best_model.named_steps.keys())[-1]], 'models/logistic_model.pkl')
    # Save scaler separately if available
    scaler = None
    for step_name, step in best_model.named_steps.items():
        if isinstance(step, StandardScaler):
            scaler = step
            break
    if scaler is None:
        # create a scaler fitted on X
        scaler = StandardScaler().fit(X)
    joblib.dump(scaler, 'models/scaler.pkl')

    meta = {'feature_names': X.columns.tolist(), 'medians': medians}
    with open('models/features.json', 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2)

    print('Saved best model to models/logistic_model.pkl and scaler/features.json')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    args = p.parse_args()
    main(args.csv)
