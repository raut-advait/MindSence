# Quiz Evaluation Fix - Root Cause Analysis & Solution

## Problem Summary
The quiz evaluation was returning a score of **0/40** regardless of which options were selected. This indicated a fundamental issue with how the ML model was integrated with the questionnaire system.

---

## Root Cause Analysis

### The Feature Mismatch Issue
The trained ML model and the quiz collect **completely different features**:

#### ML Model Features (from Student Mental Health.csv dataset)
```
- age (numeric: years)
- gender (0=male, 1=female, 2=other)
- cgpa (numeric: GPA)
- year (numeric: year of study)
- course (numeric: encoded course ID)
- depression (binary: 0/1)
- anxiety (binary: 0/1)
- panic (binary: 0/1)
- sought_treatment (binary: 0/1)
```
**Total: 9 features**

#### Quiz Features (from test.html)
```
- stress (Likert scale: 1-5)
- anxiety (Likert scale: 1-5)
- sleep (Likert scale: 1-5)
- focus (Likert scale: 1-5)
- social (Likert scale: 1-5)
- sadness (Likert scale: 1-5)
- energy (Likert scale: 1-5)
- overwhelm (Likert scale: 1-5)
```
**Total: 8 features**

### The Failed Integration Attempt
When a student submitted the quiz, the `predict_ml()` function tried to map quiz responses to model features:

```
For each of 9 model features:
  IF field name exists in quiz responses: use quiz value
  ELSE: use median value from training data

Result: [19.0, 1.0, 1.99, 2.0, 7.0, 0.0, anxiety_score, 0.0, 0.0]
         ↑age   ↑gender ↑cgpa ↑year ↑course ↑depression ↑anxiety(only match!)
```

**Only the 'anxiety' field matched.** All other 8 features used median default values:
- age = 19.0 (median)
- gender = 1.0 (median)
- cgpa = 1.99 (median)
- year = 2.0 (median)
- course = 7.0 (median)
- depression = 0.0 (median)
- panic = 0.0 (median)
- sought_treatment = 0.0 (median)

**Result:** The model received nearly identical input every time, producing a constant probability of ~0.003, which converted to a score of **0/40**.

### Secondary Bug
Additionally, the rule-based fallback had a **dimension inversion bug**:
- `focus` and `energy` were NOT inverted when they should have been
- This meant low focus/energy didn't properly increase the risk score

---

## Solution Implemented

### Fix #1: Disable Broken ML Integration
Modified `predict_ml()` to return `None, None` immediately, forcing the system to use the rule-based scoring that actually works with the quiz dimensions.

```python
def predict_ml(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm):
    """The trained model uses demographic features (age, gender, cgpa, etc.)
    which don't align with the quiz's 8 dimensions. Direct mapping is unreliable.
    Returns None to force rule-based scoring."""
    return None, None
```

### Fix #2: Correct Dimension Inversions
Fixed the rule-based scoring to properly invert the "positive" dimensions where low values indicate problems:

```python
risk_scores = {
    'stress':    scores['stress'],           # high = bad (no inversion)
    'anxiety':   scores['anxiety'],          # high = bad (no inversion)
    'sleep':     6 - scores['sleep'],        # INVERTED: low sleep = high risk ✓
    'focus':     6 - scores['focus'],        # INVERTED: low focus = high risk ✓ (FIXED)
    'social':    6 - scores['social'],       # INVERTED: isolation = high risk ✓
    'sadness':   scores['sadness'],          # high = bad (no inversion)
    'energy':    6 - scores['energy'],       # INVERTED: low energy = high risk ✓ (FIXED)
    'overwhelm': scores['overwhelm'],        # high = bad (no inversion)
}
```

---

## Score Calculation (Now Working)
Score range: **8 – 40**

| Score | Category | Meaning |
|-------|----------|---------|
| 8–16 | Excellent Mental Well-being | All answers lean positive (low stress, good sleep, etc.) |
| 17–24 | Moderate Stress Detected | Mix of good and concerning responses |
| 25–32 | High Stress & Anxiety | Most answers indicate distress |
| 33–40 | Severe Distress Detected | Consistent high stress across all dimensions |

### Example Calculations
**Scenario 1: Excellent Mental Health**
```
Input: stress=1, anxiety=1, sleep=5, focus=5, social=5, sadness=1, energy=5, overwhelm=1
Risk scores: [1, 1, 1, 1, 1, 1, 1, 1]
Total: 8/40 ✓ "Excellent Mental Well-being"
```

**Scenario 2: Severe Distress**
```
Input: stress=5, anxiety=5, sleep=1, focus=1, social=1, sadness=5, energy=1, overwhelm=5
Risk scores: [5, 5, 5, 5, 5, 5, 5, 5]
Total: 40/40 ✓ "Severe Distress Detected"
```

---

## Future Improvements

### Recommended: Retrain Model on Quiz Dimensions
To properly integrate an ML model with the quiz, the model should be retrained using:
- The 8 quiz dimensions as features (stress, anxiety, sleep, focus, social, sadness, energy, overwhelm)
- Historical quiz responses and their categorized outcomes as training data

This would enable the ML model to make predictions that actually align with the quiz data, potentially improving accuracy over the current rule-based approach.

### Temporary Workaround
The current system now uses rule-based scoring, which is simple, transparent, and aligns perfectly with the quiz interface. This is a reliable interim solution.

---

## Files Modified
1. **`app.py`**
   - Line ~100: Disabled `predict_ml()` integration
   - Line ~465: Fixed dimension inversions in rule-based scoring

## Files Created (for testing/debugging)
- `debug_model.py` - Analyzed the model/quiz mismatch
- `test_scoring_fix.py` - Validated the corrected scoring logic

---

## Verification
✓ All test cases pass (excellent, moderate, high, severe)
✓ Score ranges are mathematically correct (8–40)
✓ Dimension inversions are properly applied
✓ Quiz responses now directly impact the final score
