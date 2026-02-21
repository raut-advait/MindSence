"""Evaluate saved model on a CSV dataset and print metrics.

Usage:
  python scripts/evaluate_model.py --csv "data/Student Mental health.csv"
"""
import argparse, os, json
import pandas as pd
import joblib
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix, roc_auc_score
import numpy as np


def preprocess_for_eval(df, feature_names):
    # replicate minimal preprocessing to produce columns in feature_names
    out = {}
    if 'age' in feature_names and 'Age' in df.columns:
        out['age'] = pd.to_numeric(df['Age'], errors='coerce').fillna(df['Age'].median())
    if 'gender' in feature_names and 'Choose your gender' in df.columns:
        def map_gender(v):
            if pd.isna(v): return 0
            s=str(v).lower()
            if 'female' in s: return 1
            if 'male' in s: return 0
            return 2
        out['gender'] = df['Choose your gender'].map(map_gender)
    if 'cgpa' in feature_names and 'What is your CGPA?' in df.columns:
        out['cgpa'] = pd.to_numeric(df['What is your CGPA?'].astype(str).str.replace('[^0-9\.]','', regex=True), errors='coerce').fillna(0)
    if 'year' in feature_names and 'Your current year of Study' in df.columns:
        y = df['Your current year of Study'].astype(str).str.extract(r'(\d+)')
        out['year'] = pd.to_numeric(y[0], errors='coerce').fillna(0)
    if 'course' in feature_names and 'What is your course?' in df.columns:
        out['course'] = pd.factorize(df['What is your course?'].fillna('unknown'))[0]
    # yes/no
    def map_yesno(v):
        if pd.isna(v): return 0
        s=str(v).lower()
        if 'yes' in s or s in ('y','true','1'): return 1
        return 0
    for src, tgt in [('Do you have Depression?','depression'), ('Do you have Anxiety?','anxiety'), ('Do you have Panic attack?','panic'), ('Did you seek any specialist for a treatment?','sought_treatment')]:
        if tgt in feature_names and src in df.columns:
            out[tgt] = df[src].map(map_yesno)

    X = pd.DataFrame(out)
    # ensure all feature_names exist; missing filled with 0
    for f in feature_names:
        if f not in X.columns:
            X[f] = 0
    X = X[feature_names]
    return X


def main(csv_path):
    if not os.path.exists(csv_path):
        raise SystemExit('CSV not found: ' + csv_path)
    if not os.path.exists('models/logistic_model.pkl'):
        raise SystemExit('Model not found in models/logistic_model.pkl')

    df = pd.read_csv(csv_path)
    meta = json.load(open('models/features.json','r',encoding='utf-8'))
    feature_names = meta['feature_names']

    X = preprocess_for_eval(df, feature_names)
    # construct target same as training (sum and median threshold)
    total = X.sum(axis=1)
    y = (total > total.median()).astype(int)

    # load model and scaler
    model = joblib.load('models/logistic_model.pkl')
    scaler = joblib.load('models/scaler.pkl')

    Xs = scaler.transform(X)
    y_pred = model.predict(Xs)
    y_prob = model.predict_proba(Xs)[:,1] if hasattr(model, 'predict_proba') else None

    print('Dataset rows:', len(df))
    print('Accuracy:', accuracy_score(y, y_pred))
    print('Classification report:\n', classification_report(y, y_pred))
    print('Confusion matrix:\n', confusion_matrix(y, y_pred))
    if y_prob is not None:
        try:
            print('ROC AUC:', roc_auc_score(y, y_prob))
        except Exception:
            pass


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    args = p.parse_args()
    main(args.csv)
