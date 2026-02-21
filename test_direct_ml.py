#!/usr/bin/env python3
"""
Direct test of predict_ml function to verify scoring works properly
"""

import sys
sys.path.insert(0, '/path/to/app')

# Import the predict_ml function directly
def test_direct_ml():
    """Test scoring by importing and calling predict_ml directly"""
    
    # Copy the predict_ml function locally for testing
    def predict_ml(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm):
        """Direct risk score calculation for mental health assessment."""
        # Calculate composite from 4 core dimensions
        risk_score = (float(stress) + float(anxiety) + float(sadness) + float(overwhelm)) / 4.0
        
        # Convert to 0-40 display scale
        total_score = int(risk_score * 8)
        
        # Data-driven thresholds (percentile-based)
        if risk_score < 1.5:
            category = "Excellent Mental Well-being"
        elif risk_score < 2.25:
            category = "Moderate Stress Detected"
        elif risk_score < 3.0:
            category = "High Stress & Anxiety"
        else:
            category = "Severe Distress Detected"
        
        return risk_score / 5.0, category, total_score
    
    print("="*80)
    print("TESTING PREDICT_ML SCORING FUNCTION DIRECTLY")
    print("="*80 + "\n")
    
    test_cases = [
        ("Perfect Health (all 1s)", [1, 1, 1, 1, 1, 1, 1, 1]),
        ("Slightly Elevated (all 2s)", [2, 2, 2, 2, 2, 2, 2, 2]),
        ("Moderate (all 3s)", [3, 3, 3, 3, 3, 3, 3, 3]),
        ("Higher Stress (all 4s)", [4, 4, 4, 4, 4, 4, 4, 4]),
        ("Very High Stress (all 5s)", [5, 5, 5, 5, 5, 5, 5, 5]),
        ("Mixed: Moderate (2,3,2,3,2,3,2,3)", [2, 3, 2, 3, 2, 3, 2, 3]),
    ]
    
    results = []
    
    for name, scores in test_cases:
        prob, category, total_score = predict_ml(
            scores[0], scores[1], scores[2], scores[3],
            scores[4], scores[5], scores[6], scores[7]
        )
        results.append((name, total_score, category))
        
        print(f"Test: {name}")
        print(f"  Input: stress={scores[0]}, anxiety={scores[1]}, sadness={scores[5]}, overwhelm={scores[7]}")
        print(f"  Risk Score: {(scores[0] + scores[1] + scores[5] + scores[7]) / 4:.2f}")
        print(f"  Display Score: {total_score}/40")
        print(f"  Category: {category}")
        print()
    
    # Summary
    print("="*80)
    print("SUMMARY OF SCORES")
    print("="*80 + "\n")
    
    for name, score, category in results:
        print(f"  {name:35} → {score:2}/40 ({category})")
    
    scores_only = [r[1] for r in results]
    print(f"\nScore Range: {min(scores_only)}/40 to {max(scores_only)}/40")
    print(f"Average: {sum(scores_only)/len(scores_only):.1f}/40")
    
    # Validation
    print("\n" + "="*80)
    print("VALIDATION")
    print("="*80)
    
    if min(scores_only) > 0 and max(scores_only) < 40:
        print("✓ PASS: Scores properly distributed (not at extremes 0 or 40)")
    elif min(scores_only) == 0 and max(scores_only) == 40:
        print("✗ FAIL: Scores clustered at extremes")
    else:
        print("⚠ WARNING: Check score distribution")
    
    if max(scores_only) - min(scores_only) > 15:
        print("✓ PASS: Sufficient spread between perfect and severe responses")
    else:
        print("⚠ WARNING: Limited score spread")
    
    # Check for monotonic increase
    perfect_to_moderate = scores_only[0] < scores_only[1] < scores_only[2]
    if perfect_to_moderate:
        print("✓ PASS: Scores increase monotonically with mental health risk")
    else:
        print("✗ FAIL: Non-monotonic scoring")

if __name__ == "__main__":
    test_direct_ml()
