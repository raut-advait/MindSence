"""Preprocess and train a model from a student mental health CSV.

Usage:
    python scripts/preprocess_and_train.py --csv data/StudentMentalHealth.csv

The script tries to be robust: it will inspect columns and select numeric features.
It creates a binary "at-risk" target by thresholding a total score at the median.
Saves `models/logistic_model.pkl` and `models/scaler.pkl`.
"""
import argparse
import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import json


def main(csv_path, out_dir):
    if not os.path.exists(csv_path):
        raise SystemExit(f"CSV not found: {csv_path}. Place it in data/ or run scripts/download_dataset.md")

    df = pd.read_csv(csv_path)
    print("Loaded CSV:", csv_path)
    print(df.shape)
    print(df.dtypes)
    print("Columns:", df.columns.tolist())

    # Try to build meaningful features from known column names in the Kaggle dataset
    # Known columns (example): 'Choose your gender', 'Age', 'What is your CGPA?',
    # 'Your current year of Study', 'What is your course?', 'Do you have Depression?',
    # 'Do you have Anxiety?', 'Do you have Panic attack?', 'Did you seek any specialist for a treatment?'

    def map_yes_no(val):
        if pd.isna(val):
            return 0
        s = str(val).strip().lower()
        if s in ('yes','y','true','1'):
            return 1
        if s in ('no','n','false','0'):
            return 0
        # handle longer phrases
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

    # extract and create features when possible
    features = {}
    # Age
    if 'Age' in df.columns:
        features['age'] = pd.to_numeric(df['Age'], errors='coerce').fillna(df['Age'].median())

    # Gender
    if 'Choose your gender' in df.columns:
        features['gender'] = df['Choose your gender'].map(map_gender)

    # CGPA
    if 'What is your CGPA?' in df.columns:
        # try to extract numeric part
        features['cgpa'] = pd.to_numeric(df['What is your CGPA?'].astype(str).str.replace('[^0-9\.]','', regex=True), errors='coerce')
        if features['cgpa'].isna().all():
            features.pop('cgpa', None)
        else:
            features['cgpa'] = features['cgpa'].fillna(features['cgpa'].median())

    # Year of study
    if 'Your current year of Study' in df.columns:
        ycol = df['Your current year of Study'].astype(str).str.extract(r'(\d+)')
        if ycol.notna().any().any():
            features['year'] = pd.to_numeric(ycol[0], errors='coerce').fillna(0)

    # Course -> label encode
    if 'What is your course?' in df.columns:
        features['course'] = pd.factorize(df['What is your course?'].fillna('unknown'))[0]

    # Mental health yes/no columns
    yesno_cols = {
        'Do you have Depression?': 'depression',
        'Do you have Anxiety?': 'anxiety',
        'Do you have Panic attack?': 'panic',
        'Did you seek any specialist for a treatment?': 'sought_treatment'
    }
    for col, name in yesno_cols.items():
        if col in df.columns:
            features[name] = df[col].map(map_yes_no)

    # Build feature DataFrame
    if features:
        X = pd.DataFrame(features)
        print('Constructed features:', X.columns.tolist())
    else:
        # Fallback to numeric columns if we couldn't construct features
        numeric = df.select_dtypes(include=['int64','float64']).columns.tolist()
        if numeric:
            X = df[numeric].fillna(0)
            print('Fallback numeric features:', X.columns.tolist())
        else:
            raise SystemExit('No usable features could be constructed. Inspect dataset manually.')

    # Fill any remaining missing values
    X = X.fillna(X.median())

    # Create a simple total_score for supervision (sum of feature columns)
    total_score = X.sum(axis=1)

    # Binary target: at-risk if total_score > median (customize as needed)
    y = (total_score > total_score.median()).astype(int)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Scale
    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    # Train logistic regression (simple baseline)
    clf = LogisticRegression(max_iter=500)
    clf.fit(X_train_s, y_train)

    # Evaluate
    y_pred = clf.predict(X_test_s)
    print("Classification report:")
    print(classification_report(y_test, y_pred))

    # Save model and scaler
    os.makedirs(out_dir, exist_ok=True)
    model_path = os.path.join(out_dir, "logistic_model.pkl")
    scaler_path = os.path.join(out_dir, "scaler.pkl")
    joblib.dump(clf, model_path)
    joblib.dump(scaler, scaler_path)
    # Save feature metadata (order and medians) so the app can construct inputs
    meta = {
        'feature_names': X.columns.tolist(),
        'medians': {k: float(v) for k, v in X.median().to_dict().items()}
    }
    with open(os.path.join(out_dir, 'features.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("Saved", model_path, scaler_path)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--out', default='models')
    args = p.parse_args()
    main(args.csv, args.out)
