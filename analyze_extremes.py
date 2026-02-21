"""
Analyze the training data distribution to understand extreme predictions
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("TRAINING DATA ANALYSIS - Understanding Extreme Predictions")
print("=" * 80)

# Load cleaned data
df = pd.read_csv('data/students_mental_health_survey_cleaned.csv')

print(f"\nDataset shape: {df.shape}")
print(f"Total records: {len(df)}")

# Calculate the risk score like we did in training
risk_score = (
    df['Stress_Level'] + 
    df['Anxiety_Score'] + 
    df['Depression_Score'] + 
    df['Financial_Stress']
) / 4.0

threshold = risk_score.median()

print(f"\n" + "=" * 80)
print("RISK SCORE DISTRIBUTION (Training Target Variable)")
print("=" * 80)

print(f"\nRisk Score Stats:")
print(f"  Min:        {risk_score.min():.2f}")
print(f"  Max:        {risk_score.max():.2f}")
print(f"  Mean:       {risk_score.mean():.2f}")
print(f"  Median:     {risk_score.median():.2f}")
print(f"  Std Dev:    {risk_score.std():.2f}")

print(f"\nBinary Classification Threshold: {threshold:.2f}")
print(f"  Records below threshold (Class 0 - Well):     {(risk_score < threshold).sum()} ({(risk_score < threshold).sum()/len(df)*100:.1f}%)")
print(f"  Records at/above threshold (Class 1 - Risk):  {(risk_score >= threshold).sum()} ({(risk_score >= threshold).sum()/len(df)*100:.1f}%)")

print(f"\n" + "=" * 80)
print("PERCENTILE ANALYSIS")
print("=" * 80)

percentiles = [10, 25, 50, 75, 90, 95, 99]
for p in percentiles:
    val = np.percentile(risk_score, p)
    print(f"  {p}th percentile:  {val:.2f}")

# Check individual dimension distributions
print(f"\n" + "=" * 80)
print("INDIVIDUAL DIMENSION DISTRIBUTIONS")
print("=" * 80)

dims = ['Stress_Level', 'Anxiety_Score', 'Depression_Score', 'Financial_Stress']
for dim in dims:
    print(f"\n{dim}:")
    print(f"  Min: {df[dim].min()}, Max: {df[dim].max()}, Mean: {df[dim].mean():.2f}, Median: {df[dim].median()}")
    print(f"  Distribution: {dict(df[dim].value_counts().sort_index())}")

# Check composite scores
print(f"\n" + "=" * 80)
print("COMPOSITE SCORE PATTERNS")
print("=" * 80)

print(f"\nHow many records fall in each risk score range:")
ranges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
for low, high in ranges:
    count = ((risk_score >= low) & (risk_score < high)).sum()
    pct = count / len(df) * 100
    print(f"  {low:.1f} - {high:.1f}: {count:5} records ({pct:5.1f}%)")

print(f"\n" + "=" * 80)
print("PROBLEM Analysis")
print("=" * 80)

print("""
The issue: Training data has BINARY separation, not gradual distribution.

Why extreme coefficients exist:
  1. The threshold (2.25) cuts data into two clear groups
  2. Group 1 (scores 0.0-2.25): Mostly "Well" students
  3. Group 2 (scores 2.25-5.0): Mostly "At-Risk" students
  4. Very little overlap between groups
  5. Model learns to separate perfectly → extreme coefficients

Result:
  • Prediction is "all or nothing" (0% or 100% probability)
  • Middle range responses get classified as 100% at-risk
  • Only perfect scores get classified as 0% risk

Solution Options:
  1. Use probability calibration (adjust thresholds, not retrain)
  2. Retrain with softer target variable (probabilistic instead of binary)
  3. Use different threshold (more balanced split)
  4. Add regularization or use different algorithm
""")

print(f"\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)

print("""
BEST FIX: Recalibrate the probability thresholds

Current thresholds (based on binary classifier):
  < 0.3  → Excellent
  0.3-0.5 → Moderate
  0.5-0.75 → High
  ≥ 0.75 → Severe

Problem: Model outputs only ~0.0 or ~1.0, never 0.3-0.75

NEW approach: Map risk scores directly to categories
  Risk Score 0.0-1.0 → Excellent
  Risk Score 1.0-2.0 → Moderate
  Risk Score 2.0-3.0 → High
  Risk Score 3.0-5.0 → Severe

This bypasses the extreme probabilities and uses the actual risk scores!
""")
