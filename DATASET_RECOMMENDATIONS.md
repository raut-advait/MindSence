# Recommended Datasets for Student Mental Health Assessment

## Best Match Datasets

### 1. **DASS-21 (Depression, Anxiety, Stress Scale)**
- **Source**: Clinical Psychology Research datasets, publicly available
- **Dimensions**: Depression, Anxiety, Stress (subscales aligned with your needs)
- **Format**: Likert scale (0-3) responses to 21 questions
- **Advantages**:
  - ✓ Clinically validated psychological assessment
  - ✓ Direct alignment with stress & anxiety dimensions
  - ✓ Can be mapped to your 8 dimensions
  - ✓ Multiple versions available (DASS-21, DASS-42)
- **Where to find**: 
  - Kaggle: Search "DASS-21 dataset"
  - Research repositories: Dr. Lovibond's Psychology Lab (UNSW Sydney)

**Mapping potential**: 
```
DASS-21 Anxiety → Your "anxiety" dimension
DASS-21 Stress → Your "stress" + "overwhelm" dimensions
DASS-21 Depression → Your "sadness" dimension
(Still need: sleep, focus, social, energy)
```

---

### 2. **Kaggle: Students Mental Health Dataset** 
- **Source**: Kaggle competition datasets on student mental health
- **Keyword search**: "students mental health stress"
- **Examples**:
  - "Student Mental Health Assessment" datasets
  - "Anxiety and Stress Dataset"
  - "College Student Mental Health"
- **Advantages**:
  - ✓ Already focuses on college/university students (your target audience)
  - ✓ Often includes psychological assessment questions
  - ✓ May have pre-labeled risk categories
  - ✓ Realistic data distribution for your use case

---

### 3. **Sleep Quality & Sleep Disorders Datasets**
- **Source**: UCI Machine Learning Repository, Kaggle
- **Dataset**: "Pittsburgh Sleep Quality Index (PSQI)" studies
- **Includes**: Sleep duration, sleep quality, sleep disturbances
- **Advantages**:
  - ✓ Clinical sleep assessment tool
  - ✓ Maps directly to your "sleep" dimension
  - ✓ Can combine with other mental health datasets
- **Where to find**: 
  - UCI ML Repository: `https://archive.ics.uci.edu/`
  - Search terms: "sleep quality", "PSQI"

---

### 4. **UCLA College Student Stress & Wellbeing Study**
- **Source**: published research datasets, often available through data repositories
- **Coverage**: Stress, anxiety, academic performance, social connection, sleep
- **Advantages**:
  - ✓ Specifically designed for college students
  - ✓ Multi-dimensional assessment
  - ✓ Includes many of your 8 dimensions
  - ✓ Realistic student scenarios

---

### 5. **Open Source Psychology Datasets**
- **Source**: Open Science Framework (OSF), Harvard Dataverse
- **Relevant datasets**:
  - "Mental Well-being and Quality of Life" studies
  - "Student Burnout and Mental Health" research
  - "Sleep and Academic Performance" correlations
- **Advantages**:
  - ✓ Published research-backed
  - ✓ Detailed documentation
  - ✓ Ethically collected and licensed
- **Where to find**: 
  - `https://osf.io/` - Search mental health
  - `https://dataverse.harvard.edu/`

---

## Ideal Solution: Hybrid/Composite Dataset

### Create Your Own Labeled Dataset
Since no single dataset perfectly matches all 8 dimensions, the **best long-term solution** is to create a labeled dataset specifically for your project:

#### Option A: Collect Your Own Data
```
1. Deploy the quiz to real students
2. Collect responses over 2-3 weeks
3. Label outcomes with counselor feedback (if available)
4. Build training dataset from your actual user base
5. Train model on your specific population
```
**Benefits**: 
- ✓ Perfect feature alignment
- ✓ Domain-specific accuracy
- ✓ Reflects your actual user population
- ✓ Continuously improve as you get more data

#### Option B: Combine Existing Datasets
```
1. DASS-21 → stress, anxiety, sadness dimensions
2. Sleep Quality dataset → sleep dimension  
3. Social Network survey data → social dimension
4. Energy/Fatigue scales → energy dimension
5. Focus/Attention assessment → focus dimension
```

---

## Quick Reference: Dataset Mapping

| Your Dimension | Best Source Dataset | Notes |
|---|---|---|
| **Stress** | DASS-21 Stress subscale | Direct mapping |
| **Anxiety** | DASS-21 Anxiety subscale | Direct mapping |
| **Sleep** | Pittsburgh Sleep Quality Index | Validated sleep assessment |
| **Focus** | Cognitive Assessment batteries | Add from focus/attention studies |
| **Social** | Social Well-being scales | UCLA Social Connection scale |
| **Sadness** | DASS-21 Depression subscale | Maps to mood dimension |
| **Energy** | Fatigue/Vitality scales | PANAS energy items |
| **Overwhelm** | Perceived Stress Scale (PSS) | Measures overwhelm directly |

---

## Immediate Action Items

### Priority 1: Quick Start (1-2 hours)
1. Search Kaggle for "student mental health" + "stress" datasets
2. Download 1-2 promising datasets
3. Explore their structure and feature overlap
4. Map existing features to your 8 dimensions

### Priority 2: Medium Term (1-2 weeks)
1. Gather data from your quiz (if possible)
2. Combine Kaggle dataset + DASS-21 subscales
3. Create hybrid training dataset
4. Retrain LogisticRegression model

### Priority 3: Long Term (ongoing)
1. Continuously collect real user quiz responses
2. Build historical database of quiz outcomes
3. Refine model monthly as you gather more data
4. Validate against counselor assessments (if available)

---

## Resources

### Kaggle Datasets
- Search: `https://www.kaggle.com/datasets?search=student+mental+health`
- Filter by: CSV format, >100 rows, actively used

### Academic Repositories
- Open Science Framework: `https://osf.io/`
- Harvard Dataverse: `https://dataverse.harvard.edu/`
- UCI Machine Learning: `https://archive.ics.uci.edu/`

### Grey Literature & Studies
- Google Scholar: Search "student mental health dataset"
- ResearchGate: Researchers often share datasets
- Author repositories: Check published papers for supplementary data

---

## Recommendation

**Start with DASS-21 + a Kaggle student mental health dataset combination.**

This gives you:
- ✓ Clinically validated assessment tool
- ✓ Real student data
- ✓ Reasonable feature overlap with your 8 dimensions
- ✓ Enough samples to train a reliable model
- ✓ Clear path to improve over time

Would you like me to help you:
1. Search for specific datasets on Kaggle?
2. Create a data preprocessing script to map any dataset to your 8 dimensions?
3. Build a synthetic dataset generator for testing purposes?
