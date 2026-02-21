"""Run ML predictions for rows in `imported_test_results` and write back results."""
import sqlite3
import os
import joblib
import json
import numpy as np


def load_model_and_meta(models_dir='models'):
    model_path = os.path.join(models_dir, 'logistic_model.pkl')
    scaler_path = os.path.join(models_dir, 'scaler.pkl')
    features_path = os.path.join(models_dir, 'features.json')
    if not (os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(features_path)):
        raise SystemExit('Model, scaler, or features.json missing in models/')
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    with open(features_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    return model, scaler, meta


def main(db_path='database.db'):
    if not os.path.exists(db_path):
        raise SystemExit('Database not found: ' + db_path)

    model, scaler, meta = load_model_and_meta()
    feature_names = meta['feature_names']
    medians = meta.get('medians', {})

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Ensure predicted columns exist
    try:
        cur.execute('ALTER TABLE imported_test_results ADD COLUMN predicted_prob REAL')
    except Exception:
        pass
    try:
        cur.execute('ALTER TABLE imported_test_results ADD COLUMN predicted_category TEXT')
    except Exception:
        pass

    cur.execute('SELECT id, age, gender, cgpa, year, course, depression, anxiety, panic, sought_treatment FROM imported_test_results')
    rows = cur.fetchall()
    for r in rows:
        rid = r[0]
        row_dict = dict(zip(['id','age','gender','cgpa','year','course','depression','anxiety','panic','sought_treatment'], r))
        vec = []
        for f in feature_names:
            if f in row_dict and row_dict[f] is not None:
                try:
                    vec.append(float(row_dict[f]))
                except Exception:
                    # non-numeric (e.g., course text) -> fallback to median
                    vec.append(float(medians.get(f, 0)))
            else:
                vec.append(float(medians.get(f, 0)))
        X = np.array([vec])
        Xs = scaler.transform(X)
        prob = float(model.predict_proba(Xs)[0][1])
        if prob < 0.3:
            cat = 'Excellent Mental Well-being'
        elif prob < 0.5:
            cat = 'Moderate Stress Detected'
        elif prob < 0.75:
            cat = 'High Stress & Anxiety'
        else:
            cat = 'Severe Distress Detected'

        cur.execute('UPDATE imported_test_results SET predicted_prob=?, predicted_category=? WHERE id=?', (prob, cat, rid))

    conn.commit()
    conn.close()
    print('Predictions written to imported_test_results')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='database.db')
    args = p.parse_args()
    main(args.db)
