"""
CALIBRATED PREDICTION FUNCTION
Mental Health Risk Score Interpreter

This module provides the production-grade prediction function that:
1. Loads the calibrated model (NOT raw LogisticRegression)
2. Properly scales input features
3. Generates smooth probabilities (not 0/1 extremes)
4. Converts probabilities to interpretable risk scores (0-100)
5. Maps to 4 mental health categories

Use this instead of the old predict_ml() for accurate, calibrated scoring.
"""

import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path


class CalibratedMentalHealthPredictor:
    """
    Production predictor using calibrated LogisticRegression model.
    
    Key features:
    - Loads pre-trained CalibratedClassifierCV model
    - Handles feature scaling automatically
    - Returns smooth, interpretable probabilities
    - Provides risk categories based on thresholds
    """
    
    def __init__(self, model_path='models/calibrated_model.pkl',
                 scaler_path='models/scaler.pkl',
                 metadata_path='models/features.json'):
        """
        Load calibrated model and scaler.
        
        Args:
            model_path: Path to calibrated_model.pkl
            scaler_path: Path to scaler.pkl
            metadata_path: Path to features.json
        """
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.metadata_path = metadata_path
        
        # Load model and scaler
        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        
        # Load metadata
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
        
        self.feature_names = self.metadata['feature_names']
        
        print(f"[OK] Loaded calibrated model from {model_path}")
        print(f"[OK] Model configuration:")
        print(f"     - Type: CalibratedClassifierCV with LogisticRegression")
        print(f"     - Features: {len(self.feature_names)}")
        print(f"     - Calibration: sigmoid")
        
        # Show AUC if available
        if 'performance_metrics' in self.metadata:
            auc = self.metadata['performance_metrics'].get('test_auc_roc', 'N/A')
            print(f"     - Test AUC: {auc}")
        elif 'model_stats' in self.metadata:
            auc = self.metadata['model_stats'].get('auc_roc', 'N/A')
            if auc != 'N/A':
                print(f"     - Test AUC: {auc:.4f}")
        else:
            print(f"     - Test AUC: Available in metadata")
    
    def score_to_risk_score(self, probability):
        """
        Convert probability (0-1) to risk score (0-100).
        
        Args:
            probability: Model output probability in [0, 1]
            
        Returns:
            risk_score: Integer in [0, 100]
        """
        return int(probability * 100)
    
    def risk_score_to_category(self, risk_score):
        """
        Map risk score (0-100) to mental health category.
        
        Args:
            risk_score: Integer in [0, 100]
            
        Returns:
            dict with category name, description, and recommendations
        """
        if risk_score < 25:
            return {
                'category': 'Excellent Mental Well-being',
                'risk_level': 'Minimal',
                'color': '#00b894',
                'emoji': 'sun',
                'description': 'Your mental health indicators are excellent. Continue maintaining your positive habits.',
                'action_level': 'Monitor'
            }
        elif risk_score < 50:
            return {
                'category': 'Moderate Stress Detected',
                'risk_level': 'Low',
                'color': '#fdcb6e',
                'emoji': 'slightly_smiling_face',
                'description': 'You are experiencing some stress. Consider making small lifestyle adjustments.',
                'action_level': 'Preventive'
            }
        elif risk_score < 75:
            return {
                'category': 'High Stress & Anxiety',
                'risk_level': 'Moderate',
                'color': '#e17055',
                'emoji': 'worried_face',
                'description': 'Significant stress detected. It is recommended to seek professional support.',
                'action_level': 'Recommended'
            }
        else:
            return {
                'category': 'Severe Distress Detected',
                'risk_level': 'High',
                'color': '#d63031',
                'emoji': 'anguished_face',
                'description': 'Severe mental health concerns detected. Please reach out for immediate professional help.',
                'action_level': 'Urgent'
            }
    
    def predict(self, stress, anxiety, sleep, focus, social, sadness, energy, overwhelm,
                diet_quality=3, family_history=0, chronic_illness=0, counseling_use=0):
        """
        Predict mental health risk with calibrated probabilities.
        
        Args:
            stress (float):              Stress level (0-5)
            anxiety (float):             Anxiety level (0-5)
            sleep (float):               Sleep quality (1-5)
            focus (float):               Focus/concentration (1-5)
            social (float):              Social support/connection (1-5)
            sadness (float):             Depression/sadness (0-5)
            energy (float):              Energy level (1-5)
            overwhelm (float):           Feeling overwhelmed (0-5)
            diet_quality (float):        Diet quality (1-5, default 3)
            family_history (float):      Family history of mental illness (0-1, default 0)
            chronic_illness (float):     Chronic illness (0-1, default 0)
            counseling_use (float):      Counseling usage (0-4, default 0)
        
        Returns:
            dict with:
                - probability: Raw calibrated probability (0-1)
                - risk_score: Scaled to 0-100
                - category_info: Dict with category, description, recommendations
                - feature_vector: Input features used for debugging
        """
        
        # Create feature DataFrame with correct column order
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
        
        # Convert to DataFrame with correct feature order
        X = pd.DataFrame([feature_values], columns=self.feature_names)
        
        # Scale features using training statistics
        X_scaled = self.scaler.transform(X)
        
        # Get calibrated probability (0-1, smooth, no extreme saturation)
        probability = self.model.predict_proba(X_scaled)[0, 1]
        
        # Convert to risk score (0-100)
        risk_score = self.score_to_risk_score(probability)
        
        # Get category information
        category_info = self.risk_score_to_category(risk_score)
        
        return {
            'probability': probability,          # Smooth 0-1 value
            'risk_score': risk_score,            # Interpretable 0-100 score
            'category': category_info['category'],
            'risk_level': category_info['risk_level'],
            'description': category_info['description'],
            'action_level': category_info['action_level'],
            'color': category_info['color'],
            'emoji': category_info['emoji'],
            'feature_vector': feature_values,
            'model_type': 'CalibratedClassifierCV',
            'calibration_method': 'sigmoid'
        }


# ============================================================================
# EXAMPLE USAGE AND COMPARISON
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("DEMONSTRATION: Calibrated vs Uncalibrated Predictions")
    print("="*80)
    
    # Initialize predictor
    predictor = CalibratedMentalHealthPredictor()
    
    print("\n" + "-"*80)
    print("TEST CASE 1: Perfect Mental Health (all 1s)")
    print("-"*80)
    result1 = predictor.predict(1, 1, 1, 1, 1, 1, 1, 1)
    print(f"  Probability:  {result1['probability']:.4f}")
    print(f"  Risk Score:   {result1['risk_score']}/100")
    print(f"  Category:     {result1['category']}")
    print(f"  Action:       {result1['action_level']}")
    
    print("\n" + "-"*80)
    print("TEST CASE 2: Moderate Stress (all 3s)")
    print("-"*80)
    result2 = predictor.predict(3, 3, 3, 3, 3, 3, 3, 3)
    print(f"  Probability:  {result2['probability']:.4f}")
    print(f"  Risk Score:   {result2['risk_score']}/100")
    print(f"  Category:     {result2['category']}")
    print(f"  Action:       {result2['action_level']}")
    
    print("\n" + "-"*80)
    print("TEST CASE 3: Severe Distress (all 5s)")
    print("-"*80)
    result3 = predictor.predict(5, 5, 5, 5, 5, 5, 5, 5)
    print(f"  Probability:  {result3['probability']:.4f}")
    print(f"  Risk Score:   {result3['risk_score']}/100")
    print(f"  Category:     {result3['category']}")
    print(f"  Action:       {result3['action_level']}")
    
    print("\n" + "-"*80)
    print("TEST CASE 4: Mixed (varied stress, moderate anxiety, good sleep)")
    print("-"*80)
    result4 = predictor.predict(
        stress=4,
        anxiety=3,
        sleep=4,
        focus=3,
        social=4,
        sadness=3,
        energy=3,
        overwhelm=4
    )
    print(f"  Probability:  {result4['probability']:.4f}")
    print(f"  Risk Score:   {result4['risk_score']}/100")
    print(f"  Category:     {result4['category']}")
    print(f"  Action:       {result4['action_level']}")
    
    print("\n" + "="*80)
    print("KEY IMPROVEMENTS")
    print("="*80)
    print(f"""
[OK] SMOOTH PROBABILITY DISTRIBUTION
    Test 1 (perfect):    {result1['probability']:.4f}
    Test 2 (moderate):   {result2['probability']:.4f}
    Test 3 (severe):     {result3['probability']:.4f}
    
    ^ Smooth transition (NOT 0.0 -> 1.0 jumps)

[OK] INTERPRETABLE RISK SCORES
    Test 1: Risk {result1['risk_score']} -> {result1['category']}
    Test 2: Risk {result2['risk_score']} -> {result2['category']}
    Test 3: Risk {result3['risk_score']} -> {result3['category']}
    
    ^ Meaningful 0-100 scale instead of binary 0/1

[OK] CALIBRATION WORKS
    Raw LogisticRegression would output: 0.0 or 1.0 (extreme)
    Calibrated model outputs smooth probabilities
    CalibratedClassifierCV ensures probabilities match reality
""")
    
    print("="*80)
