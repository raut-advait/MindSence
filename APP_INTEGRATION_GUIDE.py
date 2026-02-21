"""
UPDATED APP.PY: Integration of Calibrated ML Model

This shows how to integrate the calibrated model while maintaining
backward compatibility with the direct risk scoring approach.
"""

from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
import numpy as np
import joblib
import pandas as pd
from pathlib import Path
import json

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')


# ─────────────────────────────────────────────────────────────────────────────
# PREDICTION MODELS (Two Approaches: Direct Scoring & Calibrated ML)
# ─────────────────────────────────────────────────────────────────────────────

def predict_with_direct_scoring(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm):
    """
    APPROACH 1: Direct Risk Score Calculation (SIMPLE, FAST)
    
    No ML model needed. Calculates mental health risk directly from
    the 4 core stress indicators.
    
    Pros: Simple, fast, no loading overhead, deterministic
    Cons: No pattern learning, uses only 4 of 8 dimensions
    
    Returns:
        (probability_for_display: 0-1, category: str)
    """
    # Calculate composite risk from 4 core dimensions
    risk_score = (float(stress) + float(anxiety) + float(sadness) + float(overwhelm)) / 4.0
    
    # Convert to 0-40 display scale
    total_score = int(risk_score * 8)
    
    # Data-driven thresholds
    if risk_score < 1.5:
        category = "Excellent Mental Well-being"
    elif risk_score < 2.25:
        category = "Moderate Stress Detected"
    elif risk_score < 3.0:
        category = "High Stress & Anxiety"
    else:
        category = "Severe Distress Detected"
    
    # Return probability for compatibility
    return risk_score / 5.0, category


class CalibratedMLPredictor:
    """
    APPROACH 2: Calibrated Machine Learning Model (PROFESSIONAL, SOPHISTICATED)
    
    Uses trained LogisticRegression wrapped with CalibratedClassifierCV.
    Employs all 12 features with probability calibration.
    
    Pros: ML pattern learning, all features used, well-calibrated, professional
    Cons: More complex, requires model files, prediction latency
    
    Features:
    - GridSearchCV tuned regularization (C parameter)
    - 5-fold cross-validation
    - Sigmoid probability calibration
    - Robust evaluation metrics
    """
    
    def __init__(self, model_path='models/calibrated_model.pkl',
                 scaler_path='models/scaler.pkl',
                 metadata_path='models/features.json'):
        """Load pre-trained calibrated model."""
        try:
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
            
            self.feature_names = self.metadata['feature_names']
            self.available = True
            print(f"[OK] Loaded calibrated ML model successfully")
        except Exception as e:
            print(f"[WARNING] Could not load calibrated model: {e}")
            self.available = False
    
    def predict(self, stress, anxiety, sleep, focus, social, sadness, energy, overwhelm,
                diet_quality=3, family_history=0, chronic_illness=0, counseling_use=0):
        """
        Make prediction using calibrated ML model.
        
        Args:
            All 8 core dimensions (1-5 scale)
            Plus 4 supporting features
        
        Returns:
            probability (0-1): Calibrated probability of at-risk classification
            category (str): Mental health category based on probability
        """
        
        if not self.available:
            return None, None
        
        try:
            # Create feature vector in correct order
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
            
            # Create DataFrame with correct column order
            X = pd.DataFrame([feature_values], columns=self.feature_names)
            
            # Scale features (uses training set statistics)
            X_scaled = self.scaler.transform(X)
            
            # Get calibrated probability (0-1, smooth, no extremes)
            probability = self.model.predict_proba(X_scaled)[0, 1]
            
            # Convert to category based on probability
            risk_score = probability * 100
            if risk_score < 25:
                category = "Excellent Mental Well-being"
            elif risk_score < 50:
                category = "Moderate Stress Detected"
            elif risk_score < 75:
                category = "High Stress & Anxiety"
            else:
                category = "Severe Distress Detected"
            
            return probability, category
        
        except Exception as e:
            print(f"[WARNING] Prediction error: {e}")
            return None, None


# Global predictor instance (load once at startup)
_ml_predictor = None


def get_ml_predictor():
    """Lazy load ML predictor (load only if needed)."""
    global _ml_predictor
    if _ml_predictor is None:
        _ml_predictor = CalibratedMLPredictor()
    return _ml_predictor


def predict_ml(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm,
               use_calibrated=False):
    """
    Unified prediction interface supporting both approaches.
    
    Args:
        stress, anxiety, ... overwhelm: 8 core dimension scores
        use_calibrated: If True, use ML model; if False, use direct scoring
    
    Returns:
        (probability: 0-1, category: str)
    """
    
    if use_calibrated:
        # Use professional ML approach
        predictor = get_ml_predictor()
        if predictor.available:
            return predictor.predict(stress, anxiety, sleep, focus, social,
                                   sadness, energy, overwhelm)
        else:
            # Fallback to direct scoring if ML model unavailable
            return predict_with_direct_scoring(stress, anxiety, sleep, focus,
                                             social, sadness, energy, overwhelm)
    else:
        # Use simple direct scoring
        return predict_with_direct_scoring(stress, anxiety, sleep, focus,
                                         social, sadness, energy, overwhelm)


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY ANALYSIS (Same for Both Approaches)
# ─────────────────────────────────────────────────────────────────────────────

def analyze_score_by_category(category):
    """
    Return analysis, tips, and resources based on mental health category.
    Same for both direct scoring and calibrated ML.
    """
    if category == "Excellent Mental Well-being":
        return {
            "result": "Excellent Mental Well-being",
            "status_label": "Excellent",
            "badge_class": "excellent",
            "icon": "sun",
            "description": (
                "Your mental health looks great! You're managing stress well, "
                "sleeping enough, and staying socially connected. "
                "Keep up the healthy habits."
            ),
            "tips": [
                {"emoji": "ok", "color": "green", "text": "Keep your current routine — it's working!"},
                {"emoji": "memo", "color": "blue", "text": "Consider journaling to maintain positivity."},
                {"emoji": "people", "color": "green", "text": "Help a friend — wellness multiplies."},
            ]
        }
    elif category == "Moderate Stress Detected":
        return {
            "result": "Moderate Stress Detected",
            "status_label": "Moderate",
            "badge_class": "moderate",
            "icon": "smiling_face",
            "description": (
                "You're experiencing some stress worth paying attention to. "
                "Small consistent changes can make a big difference."
            ),
            "tips": [
                {"emoji": "sleep", "color": "blue", "text": "Prioritize sleep — aim for 7-8 hours nightly."},
                {"emoji": "runner", "color": "green", "text": "Take short breaks, 20-minute walks daily."},
                {"emoji": "mute", "color": "pink", "text": "Limit social media before bedtime."},
            ]
        }
    elif category == "High Stress & Anxiety":
        return {
            "result": "High Stress & Anxiety",
            "status_label": "High",
            "badge_class": "high",
            "icon": "worried_face",
            "description": (
                "Your responses suggest significant stress and anxiety levels. "
                "It's important to take action now. Please don't ignore these signs."
            ),
            "tips": [
                {"emoji": "phone", "color": "red", "text": "Contact campus counseling or a mental health professional."},
                {"emoji": "heart", "color": "pink", "text": "Talk to a trusted friend or family member."},
                {"emoji": "exercise", "color": "green", "text": "Engage in physical activity daily."},
            ]
        }
    else:  # Severe Distress
        return {
            "result": "Severe Distress Detected",
            "status_label": "Severe",
            "badge_class": "severe",
            "icon": "anguished_face",
            "description": (
                "Your responses indicate severe mental health distress. "
                "Please reach out for immediate professional support. "
                "You are not alone, and help is available."
            ),
            "tips": [
                {"emoji": "alert", "color": "red", "text": "URGENT: Contact campus counseling immediately."},
                {"emoji": "phone", "color": "red", "text": "National Crisis Hotline: 1-800-273-8255"},
                {"emoji": "hospital", "color": "red", "text": "If in crisis, go to emergency room or call 911."},
            ]
        }


# ─────────────────────────────────────────────────────────────────────────────
# USAGE IN /predict ROUTE
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/predict', methods=['POST'])
def predict():
    """
    Evaluate quiz and return mental health assessment.
    Can use either direct scoring or calibrated ML.
    """
    if 'user' not in session:
        return redirect('/login')
    
    # Collect quiz scores
    scores = {
        'stress': int(request.form.get('stress', 3)),
        'anxiety': int(request.form.get('anxiety', 3)),
        'sleep': int(request.form.get('sleep', 3)),
        'focus': int(request.form.get('focus', 3)),
        'social': int(request.form.get('social', 3)),
        'sadness': int(request.form.get('sadness', 3)),
        'energy': int(request.form.get('energy', 3)),
        'overwhelm': int(request.form.get('overwhelm', 3)),
    }
    
    # OPTION 1: Use Direct Scoring (Fast, No ML)
    probability, category = predict_ml(**scores, use_calibrated=False)
    
    # OPTION 2: Use Calibrated ML (Sophisticated, Pattern Learning)
    # probability, category = predict_ml(**scores, use_calibrated=True)
    
    # Convert probability to display score
    total_score = int(probability * 40)
    
    # Get analysis
    analysis = analyze_score_by_category(category)
    
    # Save to database
    try:
        conn = sqlite3.connect('database.db')
        conn.execute("""
            INSERT INTO test_results
              (student_id, stress, anxiety, sleep, focus,
               social, sadness, energy, overwhelm, total_score, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.get('user_id'),
            scores['stress'], scores['anxiety'], scores['sleep'], scores['focus'],
            scores['social'], scores['sadness'], scores['energy'], scores['overwhelm'],
            total_score, analysis['result']
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
    
    return render_template('result.html', **analysis, score=total_score)


# ═════════════════════════════════════════════════════════════════════════════
# NOTES FOR IMPLEMENTATION
# ═════════════════════════════════════════════════════════════════════════════

"""
MIGRATION STRATEGY:

1. Test both approaches in staging:
   - use_calibrated=False  (Direct, currently working)
   - use_calibrated=True   (ML, for comparison)

2. Run A/B test:
   - 50% students get direct scoring
   - 50% students get calibrated ML
   - Compare results and feedback

3. Monitor metrics:
   - Score distribution (should be smooth, not clustering)
   - User satisfaction (feedback on recommendations)
   - Prediction confidence (std dev, calibration)

4. Deployment decision:
   - Keep using whichever approach works better
   - Can switch anytime without code changes
   - Maintain both for redundancy

5. Future improvements:
   - Collect more labeled data
   - Retrain models quarterly
   - Monitor for concept drift
   - A/B test new features
"""
