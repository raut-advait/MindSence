import joblib, json
import numpy as np

model = joblib.load('models/logistic_model.pkl')
print('model type:', type(model))
try:
    params = model.get_params()
    print('sample params keys:', list(params.keys())[:10])
except Exception as e:
    print('could not read params:', e)

if hasattr(model, 'coef_'):
    coef = np.array(model.coef_)
    print('coef shape:', coef.shape)
    print('coef (first row):', coef[0].tolist())
else:
    print('model has no coef_')

meta = json.load(open('models/features.json', 'r', encoding='utf-8'))
print('feature_names:', meta.get('feature_names'))
print('medians:', meta.get('medians'))
