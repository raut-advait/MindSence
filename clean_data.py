"""
Data Cleaning Script for students_mental_health_survey.csv
Removes unwanted columns, handles missing values, encodes categoricals
Outputs clean CSV ready for ML model training
"""

import pandas as pd
import numpy as np
import os

print("=" * 80)
print("DATA CLEANING PIPELINE")
print("=" * 80)

# ─────────────────────────────────────────────
# STEP 1: LOAD DATA
# ─────────────────────────────────────────────
print("\n[1/5] Loading data...")
df = pd.read_csv('data/students_mental_health_survey.csv')
print(f"✓ Loaded {len(df)} records with {len(df.columns)} columns")
print(f"  Shape: {df.shape}")

# ─────────────────────────────────────────────
# STEP 2: REMOVE UNWANTED COLUMNS
# ─────────────────────────────────────────────
print("\n[2/5] Removing irrelevant columns...")

columns_to_remove = [
    'Age',                              # Demographic
    'Course',                           # Academic, not mental health
    'Gender',                           # Demographic
    'CGPA',                             # Academic performance
    'Relationship_Status',              # Not a mental health indicator
    'Residence_Type',                   # Location not relevant
    'Semester_Credit_Load',             # Academic load
    'Extracurricular_Involvement',      # Not core to mental health
    'Substance_Use'                     # Too many missing values
]

print(f"Removing {len(columns_to_remove)} columns:")
for col in columns_to_remove:
    print(f"  ✗ {col}")

df = df.drop(columns=columns_to_remove)
print(f"\n✓ Removed columns. Remaining: {len(df.columns)}")
print(f"  Columns: {df.columns.tolist()}")

# ─────────────────────────────────────────────
# STEP 3: HANDLE MISSING VALUES
# ─────────────────────────────────────────────
print("\n[3/5] Handling missing values...")

print("Before cleaning:")
missing_before = df.isnull().sum()
if missing_before.sum() > 0:
    print(missing_before[missing_before > 0])
else:
    print("  No missing values detected")

# Drop rows with any remaining missing values (should be very few)
rows_before = len(df)
df = df.dropna()
rows_after = len(df)
rows_dropped = rows_before - rows_after

print(f"\n✓ Dropped {rows_dropped} rows with missing values")
print(f"  Rows before: {rows_before}")
print(f"  Rows after:  {rows_after}")
print(f"  Retention:   {(rows_after / rows_before * 100):.2f}%")

# ─────────────────────────────────────────────
# STEP 4: ENCODE CATEGORICAL COLUMNS
# ─────────────────────────────────────────────
print("\n[4/5] Encoding categorical columns...")

encoding_rules = {
    'Sleep_Quality': {
        'Poor': 1,
        'Average': 3,
        'Good': 5
    },
    'Physical_Activity': {
        'Low': 1,
        'Moderate': 3,
        'High': 5
    },
    'Diet_Quality': {
        'Poor': 1,
        'Average': 3,
        'Good': 5
    },
    'Social_Support': {
        'Low': 1,
        'Moderate': 3,
        'High': 5
    },
    'Family_History': {
        'No': 0,
        'Yes': 1
    },
    'Chronic_Illness': {
        'No': 0,
        'Yes': 1
    },
    'Counseling_Service_Use': {
        'Never': 0,
        'Occasionally': 2,
        'Frequently': 4
    }
}

print("Applying encodings:")
for col, mapping in encoding_rules.items():
    if col in df.columns:
        df[col] = df[col].map(mapping)
        unique_vals = sorted(df[col].unique())
        print(f"  ✓ {col:30} → {unique_vals}")
    else:
        print(f"  ✗ {col} not found in dataframe")

# ─────────────────────────────────────────────
# STEP 5: VALIDATE AND SAVE
# ─────────────────────────────────────────────
print("\n[5/5] Validating and saving...")

# Check data types
print(f"\nFinal data types:")
print(df.dtypes)

# Check for any remaining non-numeric columns
non_numeric = df.select_dtypes(exclude=['int64', 'float64']).columns.tolist()
if non_numeric:
    print(f"\n⚠ Warning: Found non-numeric columns: {non_numeric}")
    print("  These may cause issues with ML model training")
else:
    print(f"\n✓ All columns are numeric - ready for ML training")

# Check for NaN values
if df.isnull().sum().sum() == 0:
    print(f"✓ No missing values in final dataset")
else:
    print(f"⚠ Warning: Found missing values in cleaned data")

# Save cleaned data
output_path = 'data/students_mental_health_survey_cleaned.csv'
os.makedirs('data', exist_ok=True)
df.to_csv(output_path, index=False)
print(f"\n✓ Saved cleaned data to: {output_path}")

# ─────────────────────────────────────────────
# SUMMARY STATISTICS
# ─────────────────────────────────────────────
print("\n" + "=" * 80)
print("CLEANED DATASET SUMMARY")
print("=" * 80)

print(f"\nShape:        {df.shape[0]} rows × {df.shape[1]} columns")
print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")

print(f"\nFeature Statistics:")
print("-" * 80)
summary = df.describe().T
for col in df.columns:
    print(f"{col:30} → min: {df[col].min():5.1f}, max: {df[col].max():5.1f}, "
          f"mean: {df[col].mean():5.2f}, std: {df[col].std():5.2f}")

print("\n" + "-" * 80)
print("Mapping to Your 8 Dimensions:")
print("-" * 80)

mapping_to_dims = {
    'Stress_Level': '→ 1. STRESS',
    'Anxiety_Score': '→ 2. ANXIETY',
    'Sleep_Quality': '→ 3. SLEEP',
    'Physical_Activity': '→ 4. FOCUS + 7. ENERGY',
    'Social_Support': '→ 5. SOCIAL',
    'Depression_Score': '→ 6. SADNESS',
    'Financial_Stress': '→ 8. OVERWHELM',
    'Diet_Quality': '→ 3. SLEEP + 7. ENERGY (supporting)',
    'Family_History': '→ Risk predictor',
    'Chronic_Illness': '→ 4. FOCUS + 7. ENERGY (modifier)'
}

for col, mapping in mapping_to_dims.items():
    print(f"  {col:30} {mapping}")

print("\n" + "=" * 80)
print("✓ DATA CLEANING COMPLETE!")
print("=" * 80)
print(f"""
Ready for ML model training!

Next steps:
  1. Run: python train_new_model.py
  2. This will train the LogisticRegression model on cleaned data
  3. Model files will be saved to models/

Files created:
  ✓ data/students_mental_health_survey_cleaned.csv
""")
