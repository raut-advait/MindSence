"""Utility to test the saved model with manual 8-question inputs.

Usage:
  python scripts/test_manual_input.py 5 5 5 5 5 5 5 5
"""
import sys, joblib, json
import numpy as np

vals = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else [5]*8
keys = ['stress','anxiety','sleep','focus','social','sadness','energy','overwhelm']
form_vals = dict(zip(keys, vals))

meta = json.load(open('models/features.json','r',encoding='utf-8'))
fnames = meta['feature_names']
medians = meta['medians']

proxies = {}
proxies['anxiety'] = form_vals.get('anxiety', medians.get('anxiety',0))
proxies['depression'] = 1.0 if form_vals.get('sadness',0) >= 4 else 0.0
proxies['panic'] = 1.0 if form_vals.get('overwhelm',0) >= 4 else 0.0
high_count = sum(1 for v in form_vals.values() if float(v) >= 4)
proxies['sought_treatment'] = 1.0 if high_count >= 3 else 0.0

vec = []
for f in fnames:
    if f in form_vals:
        vec.append(float(form_vals[f]))
    elif f in proxies:
        vec.append(float(proxies[f]))
    else:
        vec.append(float(medians.get(f,0)))

X = np.array([vec])
model = joblib.load('models/logistic_model.pkl')
scaler = joblib.load('models/scaler.pkl')
Xs = scaler.transform(X)
prob = model.predict_proba(Xs)[0][1]
cat = 'Excellent Mental Well-being' if prob<0.3 else ('Moderate Stress Detected' if prob<0.5 else ('High Stress & Anxiety' if prob<0.75 else 'Severe Distress Detected'))
print('input scores:', form_vals)
print('predicted probability:', prob)
print('category:', cat)
