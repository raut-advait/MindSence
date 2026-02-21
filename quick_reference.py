#!/usr/bin/env python
"""
🚀 QUICK REFERENCE CHEAT SHEET
Student Mental Health Analyzer - ML Integration
"""

print("""
╔════════════════════════════════════════════════════════════════════╗
║                    🎯 QUICK REFERENCE GUIDE                       ║
║         Student Mental Health Analyzer - ML Integration            ║
╚════════════════════════════════════════════════════════════════════╝

📋 COMMON COMMANDS
═══════════════════════════════════════════════════════════════════════

1️⃣  INITIAL SETUP (First time only)
────────────────────────────────────────────────────────────────────
   python app.py                          # Start Flask (press Ctrl+C)
   python generate_test_data.py           # Generate 30 students, 75 tests
   python train_model.py                  # Train ML model


2️⃣  LOAD EXTERNAL DATASETS
────────────────────────────────────────────────────────────────────
   python load_external_data.py           # Interactive dataset loader
   
   Supports:
   • Kaggle Student Mental Health CSV
   • Mental Health in Tech Survey CSV
   • Custom CSV with column mapping


3️⃣  RUN THE APP
────────────────────────────────────────────────────────────────────
   python app.py                          # Start server on localhost:5000
   
   Then visit: http://localhost:5000


4️⃣  CHECK DATABASE STATUS
────────────────────────────────────────────────────────────────────
   python test_loader.py                  # View data distribution


5️⃣  RETRAIN MODEL
────────────────────────────────────────────────────────────────────
   python train_model.py                  # Retrains with all data in DB


6️⃣  CLEAR & RESTART
────────────────────────────────────────────────────────────────────
   python generate_test_data.py           # Type 'yes' to clear DB


📊 PROJECT FILES
═════════════════════════════════════════════════════════════════════

CORE APPLICATION:
  app.py                    → Flask app with ML integration
  database.db               → SQLite database with students & results
  
ML TRAINING:
  train_model.py            → Train Logistic Regression model
  models/logistic_model.pkl → Saved ML model (binary classification)
  models/scaler.pkl         → Feature scaler (normalization)
  
DATA GENERATION:
  generate_test_data.py     → Create synthetic test data
  load_external_data.py     → Load datasets from Kaggle/CSV
  test_loader.py            → Check database contents
  
TEMPLATES:
  templates/home.html               → Landing page
  templates/register.html           → Student registration
  templates/login.html              → Student login
  templates/test.html               → Mental health test form
  templates/result.html             → Results with ML prediction
  templates/student_dashboard.html  → Student history
  
DOCUMENTATION:
  COMPLETE_INTEGRATION_GUIDE.md  → Full architecture & workflow
  DATASET_INTEGRATION_GUIDE.md   → How to add datasets


🤖 MODEL ARCHITECTURE
═════════════════════════════════════════════════════════════════════

Input Features (8 scales, 1-5 each):
  stress, anxiety, sleep, focus, social, sadness, energy, overwhelm

Model Type: Logistic Regression
  • Binary classification (at-risk vs not at-risk)
  • Outputs probability score (0-1)
  
Output Categories:
  ✅ Excellent Mental Well-being      (prob < 0.3)
  ⚠️  Moderate Stress Detected         (prob 0.3-0.5)
  🔴 High Stress & Anxiety            (prob 0.5-0.75)
  🚨 Severe Distress Detected         (prob > 0.75)


📈 DATA DISTRIBUTION (Current)
═════════════════════════════════════════════════════════════════════

Total Students:      31
Total Test Records:  76

Breakdown:
  Excellent Mental Well-being........... 17 (22.4%)
  Moderate Stress Detected.............. 30 (39.5%)
  High Stress & Anxiety................. 25 (32.9%)
  Severe Distress Detected.............  4 (5.3%)

⚠️  Recommendation: Add 150-200 more records for best results


🔄 TYPICAL WORKFLOW
═════════════════════════════════════════════════════════════════════

WEEK 1: SETUP
  Step 1: python app.py
  Step 2: python generate_test_data.py
  Step 3: python train_model.py
  → Model ready! ✅

WEEK 2: ENHANCE DATA
  Step 4: Download Kaggle dataset OR prepare your CSV
  Step 5: python load_external_data.py
  → Select option 1, 2, or 3

WEEK 3: IMPROVE MODEL
  Step 6: python train_model.py
  → See improved accuracy metrics

WEEK 4+: DEPLOY & COLLECT
  Step 7: python app.py
  → Students use the app
  → Real data accumulates

ONGOING: CONTINUOUS IMPROVEMENT
  Monthly: python train_model.py
  → Model improves with each retraining


🎯 FEATURE IMPORTANCE (What Matters Most)
═════════════════════════════════════════════════════════════════════

🔴 INCREASES RISK SCORE:
  1. Energy Level (-0.91)        Low energy = high risk
  2. Sleep Quality (-0.83)       Poor sleep = high risk
  3. Social Connection (-0.71)   Isolation = high risk
  4. Overwhelm (0.94)            Feeling overwhelmed = high risk
  5. Sadness (0.84)              Depression = high risk
  6. Focus (0.76)                Poor concentration = high risk
  7. Anxiety (0.75)              Nervousness = high risk
  8. Stress (0.67)               Stress = high risk


📥 LOADING EXTERNAL DATA - QUICK STEPS
═════════════════════════════════════════════════════════════════════

OPTION A: KAGGLE STUDENT MENTAL HEALTH
  1. Visit: https://www.kaggle.com/datasets/scolianni/student-mental-health
  2. Download CSV file
  3. Run: python load_external_data.py
  4. Select: Option 1
  5. Enter: Path to your CSV file
  ✅ Data auto-integrated!

OPTION B: YOUR OWN DATASET
  1. Create CSV with columns: stress, anxiety, sleep, focus, etc.
  2. Run: python load_external_data.py
  3. Select: Option 3 (Custom CSV)
  4. Map your columns to our 8 factors
  ✅ Data imported!

OPTION C: VIEW CURRENT DATA
  Run: python load_external_data.py
  Select: Option 4
  ✅ See database summary!


🔐 PRIVACY REMINDERS
═════════════════════════════════════════════════════════════════════

✓ Always anonymize student data (no real names/emails in datasets)
✓ Encrypt database if storing real student information
✓ Get student consent before using their data for ML training
✓ Comply with FERPA (college privacy laws)
✓ Keep model training data separate from production data
✓ Regularly audit who accesses the system


⚙️  TROUBLESHOOTING
═════════════════════════════════════════════════════════════════════

"Error: Model file not found"
  → Run: python train_model.py

"Error: Database is locked"
  → Close Flask app (Ctrl+C) before running scripts

"Error: Column not found in CSV"
  → Check column names match. Use custom mapping in load_external_data.py

"Model predictions seem wrong"
  → Retrain: python train_model.py
  → Add more diverse data via load_external_data.py

"Port 5000 already in use"
  → Use: python app.py --port=5001


📚 FILE PURPOSES AT A GLANCE
═════════════════════════════════════════════════════════════════════

Script                      Purpose                      Run When
──────────────────────────────────────────────────────────────────
app.py                      Start Flask web app           Ready to use app
train_model.py              Train ML model                After data changes
generate_test_data.py       Create synthetic data         First setup
load_external_data.py       Add external datasets         Have CSV ready
test_loader.py              Check DB contents             Want to see data
init_db.py                  Initialize empty DB           Fresh start only


🎓 UNDERSTANDING ML PREDICTIONS
═════════════════════════════════════════════════════════════════════

What the model does:
  1. Takes student's 8 factor scores
  2. Normalizes features using the scaler
  3. Passes through Logistic Regression
  4. Returns probability: 0.0 (definitely healthy) → 1.0 (definitely at-risk)
  5. Converts probability to category + confidence

Why confidence matters:
  60% confidence → Model is somewhat sure
  90% confidence → Model is very sure
  50% confidence → Model is uncertain (maybe seek expert opinion)

The model will be most confident when:
  ✅ You have +1000 training records
  ✅ Data is diverse (covers all types of students)
  ✅ Model has been retrained recently
  ✅ New data is similar to training data


💡 BEST PRACTICES
═════════════════════════════════════════════════════════════════════

1. Retrain Monthly
   Once you have 50+ real student responses, retrain monthly

2. Monitor Accuracy
   Track precision/recall to ensure model stays reliable

3. Cross-validate
   Train-test split (80/20) helps catch overfitting

4. Consult Experts
   Have counselors review predictions periodically

5. Log Everything
   Keep records of all predictions and outcomes

6. Iterate Slowly
   Change one thing at a time, measure impact


🌟 NEXT STEPS
═════════════════════════════════════════════════════════════════════

TODAY:
  □ Run setup commands above
  □ Verify app works at http://localhost:5000

THIS WEEK:
  □ Find external dataset (Kaggle recommended)
  □ Load it via load_external_data.py
  □ Retrain model to see improvement

THIS MONTH:
  □ Deploy to real students
  □ Let data accumulate
  □ Monitor predictions quality

ONGOING:
  □ Retrain model monthly
  □ Improve with more data
  □ Refine based on counselor feedback


════════════════════════════════════════════════════════════════════

Questions? See these files:
  • COMPLETE_INTEGRATION_GUIDE.md  - Full details
  • DATASET_INTEGRATION_GUIDE.md   - Dataset instructions
  • This file (read app.py code)   - Implementation details

════════════════════════════════════════════════════════════════════
""")

# Display quick command summary
import os

print("\n🔧 SYSTEM STATUS CHECK\n")

checks = {
    "Flask app": os.path.exists("app.py"),
    "Database": os.path.exists("database.db"),
    "ML Model": os.path.exists("models/logistic_model.pkl"),
    "Scaler": os.path.exists("models/scaler.pkl"),
    "Test data generator": os.path.exists("generate_test_data.py"),
    "Dataset loader": os.path.exists("load_external_data.py"),
}

for check, exists in checks.items():
    status = "✅" if exists else "❌"
    print(f"{status} {check}")

print("\n" + "="*70)
print("Ready to go! Start with: python app.py")
print("="*70 + "\n")
