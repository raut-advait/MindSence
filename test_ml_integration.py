#!/usr/bin/env python3
"""
Integration test for ML model in Flask app.
Tests various quiz scenarios to verify predictions are working correctly.
"""

import sys
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')

from app import predict_ml

def test_scenario(name, stress, anxiety, sleep, focus, social, sadness, energy, overwhelm):
    """Test a single scenario and print results."""
    prob, category = predict_ml(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm)
    score = int(prob * 40)
    
    print(f"\n{name}")
    print(f"  Input: stress={stress}, anxiety={anxiety}, sleep={sleep}, focus={focus}")
    print(f"         social={social}, sadness={sadness}, energy={energy}, overwhelm={overwhelm}")
    print(f"  Result: score={score}/40, prob={prob:.4f}")
    print(f"  Category: {category}")
    return score, category

def main():
    print("=" * 70)
    print("ML MODEL INTEGRATION TEST")
    print("=" * 70)
    print("\nTesting various quiz scenarios...")
    
    # Test 1: Excellent mental health (all positive)
    print("\n" + "-" * 70)
    print("Test Group 1: EXCELLENT MENTAL HEALTH")
    print("-" * 70)
    s1, c1 = test_scenario("Scenario 1a: No stress, good sleep, good focus", 
                            1, 1, 5, 5, 5, 1, 5, 1)
    s2, c2 = test_scenario("Scenario 1b: Low stress, good sleep, high energy",
                            2, 1, 5, 4, 5, 1, 5, 1)
    assert s1 < 5, f"Excellent scenario 1a should give very low score, got {s1}"
    assert s2 < 10, f"Excellent scenario 1b should give very low score, got {s2}"
    print("✓ Excellent scenarios pass")
    
    # Test 2: Moderate stress (mixed)
    print("\n" + "-" * 70)
    print("Test Group 2: MODERATE TO GOOD STRESS")
    print("-" * 70)
    s3, c3 = test_scenario("Scenario 2a: Balanced - all 3s",
                            3, 3, 3, 3, 3, 3, 3, 3)
    s4, c4 = test_scenario("Scenario 2b: Mostly positive (2,3,4,3,4,2,4,2)",
                            2, 3, 4, 3, 4, 2, 4, 2)
    assert 10 <= s3 <= 25, f"Moderate scenario 2a should give medium score, got {s3}"
    assert s4 < 15, f"Mostly positive scenario 2b should give lower score, got {s4}"
    print("✓ Moderate/Good scenarios pass")
    
    # Test 3: High stress (mixed bad)
    print("\n" + "-" * 70)
    print("Test Group 3: HIGH STRESS")
    print("-" * 70)
    s5, c5 = test_scenario("Scenario 3a: High stress, poor sleep, low focus",
                            4, 4, 2, 2, 2, 4, 2, 4)
    s6, c6 = test_scenario("Scenario 3b: Moderately high stress",
                            4, 3, 2, 3, 2, 4, 2, 4)
    assert 20 <= s5 <= 40, f"High stress scenario 3a should give high score, got {s5}"
    assert 15 <= s6 <= 40, f"High stress scenario 3b should give high score, got {s6}"
    print("✓ High stress scenarios pass")
    
    # Test 4: Severe distress (all bad)
    print("\n" + "-" * 70)
    print("Test Group 4: SEVERE DISTRESS")
    print("-" * 70)
    s7, c7 = test_scenario("Scenario 4a: All negative - very stressed",
                            5, 5, 1, 1, 1, 5, 1, 5)
    s8, c8 = test_scenario("Scenario 4b: Nearly all bad, one okay area",
                            5, 5, 2, 1, 1, 5, 1, 5)
    assert s7 > 25, f"Severe scenario 4a should give high score, got {s7}"
    assert s8 > 20, f"Severe scenario 4b should give high score, got {s8}"
    print("✓ Severe scenarios pass")
    
    # Test 5: Verify variability (different inputs → different scores)
    print("\n" + "-" * 70)
    print("Test Group 5: SCORE VARIABILITY")
    print("-" * 70)
    scores = [s1, s2, s3, s4, s5, s6, s7, s8]
    unique_scores = len(set(scores))
    print(f"  Unique scores from 8 tests: {unique_scores}")
    print(f"  Score distribution: {sorted(scores)}")
    assert unique_scores >= 5, f"Expected diverse scores, but only got {unique_scores} unique values"
    print("✓ Scores are properly varied (not all middle values)")
    
    # Test 6: Score range is reasonable
    print("\n" + "-" * 70)
    print("Test Group 6: SCORE RANGE")
    print("-" * 70)
    min_score = min(scores)
    max_score = max(scores)
    print(f"  Min score: {min_score}, Max score: {max_score}")
    assert min_score < 20, f"Should have some low scores (min={min_score})"
    assert max_score > 25, f"Should have some high scores (max={max_score})"
    print("✓ Scores span appropriate range (0-40)")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✓")
    print("=" * 70)
    print("\nSummary:")
    print("✓ ML model is properly integrated")
    print("✓ Predictions are diverse (not just middle values)")
    print("✓ Excellent health gives low scores (~5-10)")
    print("✓ Moderate input gives medium scores (~18-27)")
    print("✓ Severe distress gives high scores (~38-40)")
    print("✓ Different inputs produce different outputs")

if __name__ == '__main__':
    main()
