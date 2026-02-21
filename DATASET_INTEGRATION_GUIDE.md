# 📊 External Dataset Integration Guide

## Quick Start: Download & Integrate Datasets

### **Option 1: Kaggle Student Mental Health Dataset** (Recommended)

#### Step 1: Download
1. Go to: https://www.kaggle.com/datasets/scolianni/student-mental-health
2. Click "Download" (requires Kaggle account - free)
3. Extract the CSV file to your project folder
4. File will be named something like: `Student Mental health.csv`

#### Step 2: Integrate
```bash
python load_external_data.py
```
Select option `1`, then enter the CSV path:
```
student_mental_health.csv
```

---

### **Option 2: Stress Detection Dataset**

#### Step 1: Download
1. Go to: https://www.kaggle.com/datasets/ruchi798/stress-detection-data
2. Download `stress_data.csv`

#### Step 2: Integrate
```bash
python load_external_data.py
```
Select option `3` (Custom CSV), then map columns:
- `Anxiety` → `anxiety`
- `Self_esteem` → `stress`  (inverted: low esteem = high stress)
- `Mental_Health` → `sadness`

---

### **Option 3: Your Own Data (CSV Format)**

If you have college health survey data:

#### Step 1: Prepare Your CSV
Required columns (any of these):
```
stress_level, anxiety_score, sleep_hours, focus_level,
social_interaction, depression, energy_level, overwhelm_feeling
```

#### Step 2: Manual Column Mapping
```bash
python load_external_data.py
```
Select option `3`, enter your CSV path, then map each column.

---

## 📋 Supported Dataset Formats

### **Format 1: Kaggle Student Mental Health**
Columns: `age, cgpa, anxiety, panic, depression, sleep_quality, social_interaction`

### **Format 2: Mental Health in Tech**
Columns: `work_interfere, seek_help, benefits, supervisor_support`

### **Format 3: Custom CSV**
Flexible: Map any columns to our 8 factors
```
Factors: stress, anxiety, sleep, focus, social, sadness, energy, overwhelm
```

---

## 🔄 Complete Workflow

```bash
# 1. Generate initial test data
python generate_test_data.py

# 2. Train initial model
python train_model.py

# 3. Load external dataset
python load_external_data.py

# 4. Retrain model with combined data
python train_model.py

# 5. Start Flask app with improved model
python app.py
```

---

## 📊 How Data is Mapped

The loader automatically converts external datasets to your 8-factor model:

| External Dataset | Maps To | Conversion |
|---|---|---|
| anxiety_score | anxiety | Direct (normalized 1-5) |
| depression | sadness | Direct mapping |
| sleep_hours | sleep | Normalized to 1-5 scale |
| focus_level | focus | Direct mapping |
| social_interaction | social | Direct mapping |
| work_stress | stress | High stress → High value |
| energy_level | energy | Direct mapping |
| overwhelm_feeling | overwhelm | Direct mapping |

---

## 💾 Data Size Recommendations

For best model performance:
- **Minimum**: 50 test records
- **Good**: 100-500 records
- **Excellent**: 1000+ records

Current status after setup:
- Generated test data: 75 records ✅
- With external dataset: 75 + (dataset size)
- Recommended: 150+ records

---

## ⚙️ Each Source's Pros & Cons

### **Kaggle Datasets**
✅ Pros:
- Easy to download
- Already cleaned/formatted
- Large sample sizes (1000+)
- Multiple mental health datasets available

❌ Cons:
- Require account creation
- Generic (not your student population)
- May need normalization

### **Your College Health Center**
✅ Pros:
- Most relevant to your students
- Privacy-controlled
- Can customize questions

❌ Cons:
- Requires permission/FERPA compliance
- Smaller sample size
- Need manual data entry

### **Public Health APIs**
✅ Pros:
- Real-time data
- Government verified
- Large populations

❌ Cons:
- Aggregated (not individual records)
- May not match your factors
- Complex access requirements

---

## 🔐 Privacy & Ethics Considerations

⚠️ **Important**: When using datasets:
1. **Anonymize** student identities (no real names/emails in production)
2. **Comply with FERPA** (if US college)
3. **Get consent** from participants
4. **Secure storage** - encrypt sensitive data
5. **Audit trail** - log who accessed what data

---

## 📈 After Integration, Your Pipeline Is:

```
Raw Data (CSV)
     ↓
Load & Normalize (load_external_data.py)
     ↓
Database (database.db with 100+ records)
     ↓
Train Model (train_model.py)
     ↓
Improved ML Model (logistic_model.pkl)
     ↓
Flask App (app.py) with Smart Predictions
```

---

## 🎯 Next Steps

1. **Download** a Kaggle dataset (5 minutes)
2. **Run** the loader script (1 minute)
3. **Retrain** your model (1 minute)
4. **Test** predictions in your app (5 minutes)

Total time to improve model: ~12 minutes ⚡

---

## 📞 Command Reference

```bash
# View database summary
python load_external_data.py  # Select option 4

# With Kaggle data
python load_external_data.py  # Select option 1

# With custom data
python load_external_data.py  # Select option 3

# Check model performance
python train_model.py  # Shows accuracy, precision, recall, AUC

# Run app with improved model
python app.py
```

---

## 🎓 Understanding the Model Improvement

**Before external data:**
- 30 students, 75 test records
- Accuracy: 100% (but on limited data)
- Risk: Overfitting

**After external data:**
- 30 + X students, 75 + Y test records
- Accuracy: More generalizable
- Better: Real-world performance

The more diverse data you add = Better predictions on new students ✨
