#!/usr/bin/env python3
"""
Debug script to show what quiz answers correspond to each risk score.
"""
import sys
import warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, '.')

from app import predict_ml

print("=" * 80)
print("MENTAL HEALTH QUIZ: WHAT SCORES DO YOU NEED?")
print("=" * 80)
print()

print("IMPORTANT: Some questions have INVERTED scales!")
print()
print("Questions where 5 is GOOD (high values = good mental wellbeing):")
print("  • Sleep (both quality AND hours) - 5 is best")
print("  • Focus & Concentration - 5 is best")
print("  • Social Connection - 5 is best")
print("  • Energy Level - 5 is best")
print()
print("Questions where 1 is GOOD (low values = good mental health):")
print("  • Stress - 1 is best")
print("  • Anxiety - 1 is best")
print("  • Sadness/Mood - 1 is best")
print("  • Overwhelmed - 1 is best")
print()
print("-" * 80)
print()

print("PERFECT MENTAL HEALTH (Minimum Risk):")
print("  Answer: 1, 1, 5, 5, 5, 1, 5, 1")
prob, cat = predict_ml(1, 1, 5, 5, 5, 1, 5, 1)
score = int(prob * 40)
print(f"  Score: {score}/40 - {cat}")
print()

print("What each field means:")
print("  1. Stress level: 1 (None/Very Little)")
print("  2. Work/Academic stress: 1 (Very Little)")
print("  3. Anxiety: 1 (Never)")
print("  4. Sleep: 5 (9+ hours OR Excellent quality)")
print("  5. Focus: 5 (Excellent)")
print("  6. Social: 5 (Very well connected)")
print("  7. Sadness: 1 (Very happy)")
print("  8. Energy: 5 (Very High)")
print("  9. Overwhelm: 1 (Calm)")
print()
print("-" * 80)
print()

print("COMMON MISTAKES:")
print()
print("❌ Answering ALL 1s (thinking 1 is 'best'):")
prob_bad, cat_bad = predict_ml(1, 1, 1, 1, 1, 1, 1, 1)
score_bad = int(prob_bad * 40)
print(f"   Score: {score_bad}/40 - {cat_bad}")
print("   Why: Sleep hours of <4 hrs (1) is TERRIBLE, not good!")
print()

print("❌ Answering ALL 5s (thinking 5 is 'best'):")
prob_bad2, cat_bad2 = predict_ml(5, 5, 5, 5, 5, 5, 5, 5)
score_bad2 = int(prob_bad2 * 40)
print(f"   Score: {score_bad2}/40 - {cat_bad2}")
print("   Why: Stress level of 5 (Extreme) is TERRIBLE!")
print()

print("-" * 80)
print()

print("SCORE RANGE GUIDE:")
print()
scenarios = [
    ("Perfect Health (answer optimally)", 1, 1, 5, 5, 5, 1, 5, 1),
    ("Mostly Good (slight issues)", 2, 2, 4, 4, 4, 1, 4, 1),
    ("Balanced (neutral)", 3, 3, 3, 3, 3, 3, 3, 3),
    ("Some Stress (moderate issues)", 4, 3, 2, 3, 2, 4, 2, 4),
    ("Severe Stress (in crisis)", 5, 5, 1, 1, 1, 5, 1, 5),
]

for desc, s, a, sl, f, so, sa, e, o in scenarios:
    p, c = predict_ml(s, a, sl, f, so, sa, e, o)
    sc = int(p * 40)
    status = "✓ EXCELLENT" if sc < 10 else "✓ GOOD" if sc < 20 else "⚠ MODERATE" if sc < 30 else "⚠ CONCERNING" if sc < 35 else "❌ CRITICAL"
    print(f"  {status:20} | Score: {sc:2}/40 | {c}")

print()
print("=" * 80)
