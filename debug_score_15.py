#!/usr/bin/env python3
"""
Test to find what inputs give score 15 and verify model behavior.
"""
import sys
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')

from app import predict_ml

print("=" * 80)
print("DEBUGGING SCORE 15 ISSUE")
print("=" * 80)
print()

# The user reported getting score 15 with "perfect answers for good mental health"
# Let's find what mix of values produces score 15

target_score = 15

print(f"Looking for combinations that produce score {target_score}...")
print()

test_cases = [
    # Different combinations that might produce 15
    ("All 2s", 2, 2, 2, 2, 2, 2, 2, 2),
    ("Low 2s with some 3s", 2, 2, 3, 3, 3, 2, 3, 2),
    ("Mixed: 1,1 for risk + 4,4 for protection", 1, 1, 4, 4, 4, 1, 4, 1),
    ("Mixed: 2,2 for risk + 4,4 for protection", 2, 2, 4, 4, 4, 2, 4, 2),
    ("Mixed: 3,3 for risk + 3,3 for protection", 3, 3, 3, 3, 3, 3, 3, 3),
    ("High on positive areas", 1, 1, 5, 4, 5, 1, 5, 1),
    ("Low on both", 1, 1, 1, 2, 2, 1, 1, 1),
]

for desc, s, a, sl, f, so, sa, e, o in test_cases:
    p, c = predict_ml(s, a, sl, f, so, sa, e, o)
    score = int(p * 40)
    print(f"({s},{a},{sl},{f},{so},{sa},{e},{o}) → Score: {score:2} | {desc}")
    print(f"                    Category: {c}")
    if score == target_score:
        print(f"                    ⭐ MATCHES TARGET SCORE {target_score}!")
    print()

print("=" * 80)
print()
print("ANALYSIS: What's happening?")
print()
print("The model appears to treat the input features as risk factors where:")
print("  - Lower values = Lower risk (good mental health)")
print("  - Higher values = Higher risk (poor mental health)")
print()
print("This might be OPPOSITE to what you expect for some fields!")
print()
print("For example:")
print("  • Sleep: You might expect 5=good, 1=bad")
print("  • Focus: You might expect 5=good, 1=bad")
print("  • But the model learned that 1s = healthy, 5s = at-risk")
print()
print("This is because the model was trained on a specific dataset encoding.")
print()
