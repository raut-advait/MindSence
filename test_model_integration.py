"""
Test script to verify the trained model works correctly with the quiz system
"""
import sys
import json
import joblib
import numpy as np

print("=" * 80)
print("MODEL INTEGRATION TEST")
print("=" * 80)

# Load model components
print("\n[1] Loading model files...")
try:
    model = joblib.load('models/logistic_model.pkl')
    scaler = joblib.load('models/scaler.pkl')
    with open('models/features.json', 'r') as f:
        features_meta = json.load(f)
    print("✓ Model loaded successfully")
    print(f"  - Model type: {type(model).__name__}")
    print(f"  - Expected features: {model.n_features_in_}")
    print(f"  - Features in metadata: {len(features_meta['feature_names'])}")
except Exception as e:
    print(f"✗ Failed to load model: {e}")
    sys.exit(1)

# Test with sample quiz responses
print("\n[2] Testing with sample quiz responses...")

test_cases = [
    {
        "name": "Excellent mental health",
        "responses": {'stress': 1, 'anxiety': 1, 'sleep': 5, 'focus': 5, 'social': 5, 'sadness': 1, 'energy': 5, 'overwhelm': 1},
        "expected_category": "Excellent"
    },
    {
        "name": "Moderate stress",
        "responses": {'stress': 3, 'anxiety': 3, 'sleep': 3, 'focus': 3, 'social': 3, 'sadness': 3, 'energy': 3, 'overwhelm': 3},
        "expected_category": "Moderate"
    },
    {
        "name": "High stress and anxiety",
        "responses": {'stress': 4, 'anxiety': 4, 'sleep': 2, 'focus': 2, 'social': 2, 'sadness': 4, 'energy': 2, 'overwhelm': 4},
        "expected_category": "High"
    },
    {
        "name": "Severe distress",
        "responses": {'stress': 5, 'anxiety': 5, 'sleep': 1, 'focus': 1, 'social': 1, 'sadness': 5, 'energy': 1, 'overwhelm': 5},
        "expected_category": "Severe"
    },
]

print("\nTesting predictions:")
print("-" * 80)

passed = 0
failed = 0

for test in test_cases:
    quiz = test['responses']
    
    # Build feature vector matching the model's expected features
    fnames = features_meta['feature_names']
    medians = features_meta['medians']
    vec = []
    
    for f in fnames:
        if f in quiz:
            vec.append(float(quiz[f]))
        else:
            vec.append(float(medians.get(f, 0)))
    
    # Make prediction
    try:
        features = np.array([vec])
        features_scaled = scaler.transform(features)
        risk_prob = model.predict_proba(features_scaled)[0][1]
        
        # Map to category
        if risk_prob < 0.3:
            category = "Excellent"
        elif risk_prob < 0.5:
            category = "Moderate"
        elif risk_prob < 0.75:
            category = "High"
        else:
            category = "Severe"
        
        score = int(risk_prob * 40)
        
        # Check if matches expected
        status = "✓ PASS" if category == test['expected_category'] else "✗ FAIL"
        if category == test['expected_category']:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} - {test['name']}")
        print(f"  Risk probability: {risk_prob:.4f}")
        print(f"  Score:           {score}/40")
        print(f"  Category:        {category} (expected: {test['expected_category']})")
        
    except Exception as e:
        print(f"\n✗ FAIL - {test['name']}")
        print(f"  Error: {e}")
        failed += 1

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Passed: {passed}/{len(test_cases)}")
print(f"Failed: {failed}/{len(test_cases)}")

if failed == 0:
    print("\n✓ All tests passed! Model is ready for production.")
    print("\nThe Flask app will now:")
    print("  1. Receive 8 quiz dimension scores (1-5 scale each)")
    print("  2. Pass them to predict_ml() function")
    print("  3. Get risk probability and category back")
    print("  4. Display mental health assessment to user")
else:
    print("\n✗ Some tests failed. Check model files and features.json")

print("\n" + "=" * 80)
print("FEATURE IMPORTANCE")
print("=" * 80)
print("\nModel coefficients (impact on 'at-risk' prediction):")
feature_importance = list(zip(features_meta['feature_names'], model.coef_[0]))
feature_importance.sort(key=lambda x: abs(x[1]), reverse=True)

for feat, coef in feature_importance:
    direction = "↑ risk" if coef > 0 else "↓ risk"
    bar_length = int(abs(coef) * 100)
    bar = "█" * min(bar_length // 2, 20)
    print(f"  {feat:20} {coef:+.4f}  {bar} {direction}")

print("\n" + "=" * 80)
print("✓ MODEL INTEGRATION TEST COMPLETE")
print("=" * 80)
