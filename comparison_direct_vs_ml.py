"""
COMPARISON: Direct Scoring vs Calibrated ML
============================================

This script compares both approaches side-by-side on various test cases
to help you decide which to use in production.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path


def direct_risk_score(stress, anxiety, sadness, overwhelm):
    """APPROACH 1: Direct Risk Scoring"""
    risk_score = (float(stress) + float(anxiety) + float(sadness) + float(overwhelm)) / 4.0
    score = int(risk_score * 8)
    
    if risk_score < 1.5:
        cat = "Excellent"
    elif risk_score < 2.25:
        cat = "Moderate"
    elif risk_score < 3.0:
        cat = "High"
    else:
        cat = "Severe"
    
    return score, cat, risk_score


def calibrated_ml_score(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm,
                       diet_quality=3, family_history=0, chronic_illness=0, counseling_use=0):
    """APPROACH 2: Calibrated ML"""
    try:
        model = joblib.load('models/calibrated_model.pkl')
        scaler = joblib.load('models/scaler.pkl')
        
        import json
        with open('models/features.json', 'r') as f:
            metadata = json.load(f)
        
        feature_names = metadata['feature_names']
        feature_values = {
            'stress': float(stress),
            'anxiety': float(anxiety),
            'sleep': float(sleep),
            'focus': float(focus),
            'social': float(social),
            'sadness': float(sadness),
            'energy': float(energy),
            'overwhelm': float(overwhelm),
            'diet_quality': float(diet_quality),
            'family_history': float(family_history),
            'chronic_illness': float(chronic_illness),
            'counseling_use': float(counseling_use),
        }
        
        X = pd.DataFrame([feature_values], columns=feature_names)
        X_scaled = scaler.transform(X)
        
        prob = model.predict_proba(X_scaled)[0, 1]
        score = int(prob * 100)
        
        if score < 25:
            cat = "Excellent"
        elif score < 50:
            cat = "Moderate"
        elif score < 75:
            cat = "High"
        else:
            cat = "Severe"
        
        return score, cat, prob
    except Exception as e:
        print(f"ML Error: {e}")
        return None, None, None


print("="*100)
print("COMPARISON: DIRECT SCORING vs CALIBRATED ML")
print("="*100)

test_cases = [
    ("Perfect Health",      [1, 1, 1, 1, 1, 1, 1, 1]),
    ("Very Good",           [1, 1, 2, 2, 2, 1, 2, 1]),
    ("Good",                [2, 2, 3, 3, 3, 2, 3, 2]),
    ("Slightly Elevated",   [2, 3, 3, 3, 3, 3, 3, 3]),
    ("Moderate",            [3, 3, 3, 3, 3, 3, 3, 3]),
    ("Elevated",            [3, 4, 3, 3, 3, 4, 3, 4]),
    ("High Stress",         [4, 4, 2, 2, 2, 4, 2, 4]),
    ("Very High",           [4, 5, 2, 2, 2, 5, 2, 5]),
    ("Severe",              [5, 5, 1, 1, 1, 5, 1, 5]),
    ("Extreme",             [5, 5, 1, 1, 1, 5, 1, 5]),
]

print()
print("-"*100)
print(f"{'Test Case':<20} | {'Direct Score':^20} | {'ML Score':^20} | {'Agreement':^20}")
print(f"{'':20} | {'(Score, Cat, Risk)':^20} | {'(Score, Cat, Prob)':^20} | {'Cat Match':^20}")
print("-"*100)

direct_scores = []
ml_scores = []
matches = 0

for name, scores in test_cases:
    stress, anxiety, sleep, focus, social, sadness, energy, overwhelm = scores
    
    d_score, d_cat, d_risk = direct_risk_score(stress, anxiety, sadness, overwhelm)
    m_score, m_cat, m_prob = calibrated_ml_score(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm)
    
    direct_scores.append(d_score)
    ml_scores.append(m_score)
    
    match = "OK" if d_cat == m_cat else "DIFF"
    if d_cat == m_cat:
        matches += 1
    
    # Format output
    d_info = f"{d_score:2d}/40, {d_cat:8s}, {d_risk:.2f}"
    m_info = f"{m_score:3d}/100, {m_cat:8s}, {m_prob:.4f}" if m_score is not None else "N/A"
    
    print(f"{name:<20} | {d_info:^20} | {m_info:^20} | {match:^20}")

print("-"*100)
print()

print()
print("="*100)
print("STATISTICS")
print("="*100)

d_arr = np.array(direct_scores)
m_arr = np.array([s for s in ml_scores if s is not None])

print(f"\nDirect Scoring (0-40 scale):")
print(f"  Min:      {d_arr.min()}/40")
print(f"  Max:      {d_arr.max()}/40")
print(f"  Mean:     {d_arr.mean():.1f}/40")
print(f"  Std Dev:  {d_arr.std():.1f}")

if len(m_arr) > 0:
    print(f"\nCalibrated ML (0-100 scale):")
    print(f"  Min:      {m_arr.min()}/100")
    print(f"  Max:      {m_arr.max()}/100")
    print(f"  Mean:     {m_arr.mean():.1f}/100")
    print(f"  Std Dev:  {m_arr.std():.1f}")
    
    print(f"\nCategory Agreement: {matches}/{len(test_cases)} ({matches/len(test_cases)*100:.0f}%)")

print()
print("="*100)
print("ANALYSIS")
print("="*100)

print(f"""
DIRECT SCORING CHARACTERISTICS:
  - Score Range:     0-40 (or 0-400 if scaled to 0-20 then *20)
  - Basis:           Simple average of 4 core dimensions
  - Features Used:   4 out of 8 (stress, anxiety, sadness, overwhelm)
  - Complexity:      Very simple math (one formula)
  - Interpretability: Very easy (just averaging)
  - Speed:           Instant (no model loading)
  - Consistency:     Perfect determinism
  
  Advantages:
    + Fast (zero latency)
    + Deterministic (reproducible)
    + Simple to debug (math is clear)
    + No model files needed
    + Easy to explain to users
  
  Disadvantages:
    - Ignores 4 of 8 dimensions
    - No pattern learning
    - No feature interactions
    - No regularization benefits
    - Coarse categories

CALIBRATED ML CHARACTERISTICS:
  - Score Range:     0-100 (probability-based)
  - Basis:           LogisticRegression with 12 features
  - Features Used:   All 12 (8 core + 4 supporting)
  - Complexity:      ML model with hyperparameter tuning
  - Interpretability: Medium (model coefficients show importance)
  - Speed:           ~5-10ms per prediction (model inference)
  - Consistency:     Probabilistic (smooth distribution)
  
  Advantages:
    + Uses all 12 features
    + Pattern learning from data
    + Feature interactions captured
    + Hyperparameter optimization
    + Probability calibration
    + Professional ML approach
  
  Disadvantages:
    - Slower (model loading + inference)
    - Complex to debug (black box)
    - Requires model files
    - Model drift over time
    - Need retraining strategy
    - Harder to explain to users

RECOMMENDATION:
  
  Use DIRECT SCORING if:
    - Already working well in production
    - Speed is critical (real-time constraints)
    - Simplicity preferred over sophistication
    - Limited maintenance resources
    - Feature engineering is clear
  
  Use CALIBRATED ML if:
    - Want to leverage all 12 features
    - Pattern learning is important
    - Can afford model maintenance
    - Users appreciate probability-based output
    - Validation/calibration is documented
    - Have monitoring infrastructure

HYBRID APPROACH:
    - Use direct scoring for speed
    - Use ML in background for comparison
    - Monitor agreement rate
    - Switch if ML consistently better
    - Keep both as fallback option

YOUR SITUATION:
    Your direct scoring is WORKING WELL!
    Users are getting meaningful score distribution.
    No urgency to change.
    
    Consider ML as:
    - "Nice to have" enhancement
    - Testing ground for feature learning
    - Backup approach if direct scoring breaks
    - Future upgrade when resources available
""")

print("="*100)
