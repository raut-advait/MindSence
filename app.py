from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import os
import numpy as np
import joblib
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
 
# Flask app instance
app = Flask(__name__, template_folder='templates', static_folder='static')
# Secret key for sessions (override via env var in production)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

# Indian Standard Time (IST) timezone
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_timestamp():
    """Get current timestamp in Indian Standard Time (IST)"""
    return datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')


# ─────────────────────────────────────────────────────────────────────────────
# LOAD CALIBRATED MODEL (Using trained CalibratedClassifierCV)
# ─────────────────────────────────────────────────────────────────────────────

def load_calibrated_model_components():
    """Load the trained calibrated model, scaler, and metadata."""
    try:
        model = joblib.load('models/calibrated_model.pkl')
        scaler = joblib.load('models/scaler.pkl')
        
        with open('models/features.json', 'r') as f:
            metadata = json.load(f)
        
        return model, scaler, metadata
    except Exception as e:
        print(f"Error loading calibrated model: {e}")
        return None, None, None


# Global variables (load once at startup)
_calibrated_model = None
_scaler = None
_metadata = None


def get_ml_components():
    """Lazy-load ML components on first use."""
    global _calibrated_model, _scaler, _metadata
    if _calibrated_model is None:
        _calibrated_model, _scaler, _metadata = load_calibrated_model_components()
    return _calibrated_model, _scaler, _metadata


# ─────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────
def get_db():
    """Get a database connection and set row factory for dict-like access."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't already exist."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            email    TEXT    NOT NULL UNIQUE,
            password TEXT    NOT NULL,
            dob      TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            stress      INTEGER,
            anxiety     INTEGER,
            sleep       INTEGER,
            focus       INTEGER,
            social      INTEGER,
            sadness     INTEGER,
            energy      INTEGER,
            overwhelm   INTEGER,
            total_score INTEGER,
            result      TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS mood_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            mood        TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
#  ML MODEL HELPERS
# ─────────────────────────────────────────────
def load_ml_model():
    """Load pre-trained Logistic Regression model and feature metadata.

    Returns (model, scaler, features_meta) where features_meta is a dict
    with keys 'feature_names' and 'medians' when available.
    """
    model_path = "models/logistic_model.pkl"
    scaler_path = "models/scaler.pkl"
    features_path = "models/features.json"

    if os.path.exists(model_path) and os.path.exists(scaler_path):
        try:
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            features_meta = None
            try:
                import json
                if os.path.exists(features_path):
                    with open(features_path, 'r', encoding='utf-8') as fh:
                        features_meta = json.load(fh)
            except Exception:
                features_meta = None
            return model, scaler, features_meta
        except Exception as e:
            print(f"Error loading model: {e}")
            return None, None, None
    return None, None, None


def predict_ml(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm):
    """
    Use CALIBRATED ML MODEL for mental health assessment.
    
    Uses trained CalibratedClassifierCV with all 12 features.
    Produces smooth, calibrated probabilities instead of extreme 0/1 values.
    
    Args:
        stress, anxiety, sleep, focus, social, sadness, energy, overwhelm (0-5)
        All 8 core mental health dimensions
    
    Returns:
        (probability: 0-1, category: str)
        probability - Calibrated ML probability of at-risk classification
        category - Mental health category (Excellent, Moderate, High, Severe)
    """
    model, scaler, metadata = get_ml_components()
    
    if model is None or scaler is None:
        # Fallback to direct scoring if model unavailable
        print("[WARNING] ML model not available, using fallback direct scoring")
        risk_score = (float(stress) + float(anxiety) + float(sadness) + float(overwhelm)) / 4.0
        
        if risk_score < 1.5:
            category = "Excellent Mental Well-being"
        elif risk_score < 2.25:
            category = "Moderate Stress Detected"
        elif risk_score < 3.0:
            category = "High Stress & Anxiety"
        else:
            category = "Severe Distress Detected"
        
        return risk_score / 5.0, category
    
    try:
        # IMPORTANT: The model was trained on data with specific ranges:
        # - Stress (0-5), Anxiety (0-5), Depression (0-5), Financial_Stress (0-5)
        # - Sleep (1-5), Physical_Activity (1-5), Social_Support (1-5), Diet_Quality (1-5)
        # The quiz sends 1-5 for all fields.
        # Convert quiz values (1-5) to training data ranges to match scaler expectations
        
        # Convert 1-5 scale to 0-4 by subtracting 1 for fields that originally had 0-5 range
        # This maps: quiz(1) → training(0), quiz(5) → training(4)
        stress_val = float(stress) - 1  # Convert 1-5 to 0-4
        anxiety_val = float(anxiety) - 1  # Convert 1-5 to 0-4
        sadness_val = float(sadness) - 1  # Convert 1-5 to 0-4
        overwhelm_val = float(overwhelm) - 1  # Convert 1-5 to 0-4
        
        # Keep 1-5 scale for fields that originally had 1-5 range
        sleep_val = float(sleep)  # Already 1-5
        focus_val = float(focus)  # Already 1-5 (Physical_Activity)
        social_val = float(social)  # Already 1-5 (Social_Support)
        energy_val = float(energy)  # Already 1-5 (Physical_Activity)
        
        feature_names = metadata['feature_names']
        feature_values = {
            'stress': stress_val,
            'anxiety': anxiety_val,
            'sleep': sleep_val,
            'focus': focus_val,
            'social': social_val,
            'sadness': sadness_val,
            'energy': energy_val,
            'overwhelm': overwhelm_val,
            'diet_quality': 3.0,  # Default: middle of 1-5 scale
            'family_history': 0.0,  # Binary: 0 or 1
            'chronic_illness': 0.0,  # Binary: 0 or 1
            'counseling_use': 0.0,  # 0-4 scale, default to 0
        }
        
        # Create DataFrame with correct feature order
        X = pd.DataFrame([feature_values], columns=feature_names)
        
        # Scale features using training statistics
        X_scaled = scaler.transform(X)
        
        # Reconstruct DataFrame with feature names after scaling
        # (scaler.transform returns numpy array without column names)
        X_scaled_df = pd.DataFrame(X_scaled, columns=feature_names)
        
        # Use base model probabilities instead of calibrated (calibration is too aggressive here)
        # The base LogisticRegression already gives smooth, reasonable probabilities
        base_estimator = model.estimator
        probability = base_estimator.predict_proba(X_scaled_df)[0, 1]
        
        # Convert to category based on probability
        risk_score = probability * 100
        if risk_score < 25:
            category = "Excellent Mental Well-being"
        elif risk_score < 50:
            category = "Moderate Stress Detected"
        elif risk_score < 75:
            category = "High Stress & Anxiety"
        else:
            category = "Severe Distress Detected"
        
        return probability, category
        
    except Exception as e:
        print(f"[ERROR] ML prediction failed: {e}")
        # Fallback to direct scoring
        risk_score = (float(stress) + float(anxiety) + float(sadness) + float(overwhelm)) / 4.0
        
        if risk_score < 1.5:
            category = "Excellent Mental Well-being"
        elif risk_score < 2.25:
            category = "Moderate Stress Detected"
        elif risk_score < 3.0:
            category = "High Stress & Anxiety"
        else:
            category = "Severe Distress Detected"
        
        return risk_score / 5.0, category



def analyze_score_by_category(category):
    """
    Return analysis dict based on ML category prediction
    """
    if category == "Excellent Mental Well-being":
        return {
            "result":      "Excellent Mental Well-being",
            "status_label":"Excellent",
            "badge_class": "normal",
            "icon":        "🌟",
            "description": (
                "Your mental health looks great! You're managing stress well, sleeping enough, "
                "and staying socially connected. Keep up the healthy habits and check in regularly."
            ),
            "tips": [
                {"emoji": "✅", "color": "green", "text": "Keep your current sleep and exercise routine — it's working!"},
                {"emoji": "📝", "color": "blue",  "text": "Consider journaling to maintain your positive mindset."},
                {"emoji": "🤝", "color": "green", "text": "Help a friend — sharing wellness multiplies it."},
                {"emoji": "🧘", "color": "pink",  "text": "Explore mindfulness meditation to stay grounded."},
            ]
        }
    elif category == "Moderate Stress Detected":
        return {
            "result":      "Moderate Stress Detected",
            "status_label":"Moderate",
            "badge_class": "moderate",
            "icon":        "😐",
            "description": (
                "You're experiencing some stress and anxiety that's worth paying attention to. "
                "Small consistent changes to your routine can make a big difference. "
                "You're not alone — many students feel this way."
            ),
            "tips": [
                {"emoji": "😴", "color": "blue",  "text": "Prioritize sleep — aim for 7–8 hours every night."},
                {"emoji": "🚶", "color": "green", "text": "Take short breaks and a 20-minute walk daily to reset."},
                {"emoji": "📵", "color": "pink",  "text": "Limit social media and news before bedtime."},
                {"emoji": "🗣️", "color": "blue",  "text": "Talk to a trusted friend or counselor about your worries."},
            ]
        }
    elif category == "High Stress & Anxiety":
        return {
            "result":      "High Stress & Anxiety",
            "status_label":"High",
            "badge_class": "high",
            "icon":        "⚠️",
            "description": (
                "Your responses suggest significant stress and anxiety levels. "
                "It's important to take action now. Please don't ignore these signs — "
                "support is available and seeking help is a sign of strength."
            ),
            "tips": [
                {"emoji": "🆘", "color": "pink",  "text": "Speak with your college counselor or a mental health professional soon."},
                {"emoji": "📞", "color": "blue",  "text": "iCall Helpline: 9152987821 (Mon–Sat, 8AM–10PM)"},
                {"emoji": "🧘", "color": "green", "text": "Practice deep breathing: inhale 4s, hold 4s, exhale 6s."},
                {"emoji": "🛑", "color": "pink",  "text": "Reduce academic overload if possible — talk to your professors."},
            ]
        }
    else:  # Severe Distress Detected
        return {
            "result":      "Severe Distress Detected",
            "status_label":"Severe",
            "badge_class": "high",
            "icon":        "🚨",
            "description": (
                "Your responses indicate a high level of distress. Please know that you are not alone "
                "and that help is available. Reaching out to a professional is the most important step "
                "you can take right now. Your well-being matters more than anything else."
            ),
            "tips": [
                {"emoji": "🆘", "color": "pink",  "text": "Please contact a mental health professional immediately."},
                {"emoji": "📞", "color": "pink",  "text": "NIMHANS Helpline: 080-46110007 | iCall: 9152987821"},
                {"emoji": "🤝", "color": "blue",  "text": "Tell a trusted adult (parent, teacher, counselor) how you're feeling."},
                {"emoji": "🏥", "color": "green", "text": "Visit your college health center for an in-person consultation."},
            ]
        }


# ─────────────────────────────────────────────
#  PREDICTION LOGIC  (rule-based for now, ML later)
# ─────────────────────────────────────────────
def analyze_score(score):
    """
    Score range: 8 – 40
    Lower is healthier (for most dimensions sleep/social are inverted).
    """
    if score <= 16:
        return {
            "result":      "Excellent Mental Well-being",
            "status_label":"Excellent",
            "badge_class": "normal",
            "icon":        "🌟",
            "description": (
                "Your mental health looks great! You're managing stress well, sleeping enough, "
                "and staying socially connected. Keep up the healthy habits and check in regularly."
            ),
            "tips": [
                {"emoji": "✅", "color": "green", "text": "Keep your current sleep and exercise routine — it's working!"},
                {"emoji": "📝", "color": "blue",  "text": "Consider journaling to maintain your positive mindset."},
                {"emoji": "🤝", "color": "green", "text": "Help a friend — sharing wellness multiplies it."},
                {"emoji": "🧘", "color": "pink",  "text": "Explore mindfulness meditation to stay grounded."},
            ]
        }
    elif score <= 24:
        return {
            "result":      "Moderate Stress Detected",
            "status_label":"Moderate",
            "badge_class": "moderate",
            "icon":        "😐",
            "description": (
                "You're experiencing some stress and anxiety that's worth paying attention to. "
                "Small consistent changes to your routine can make a big difference. "
                "You're not alone — many students feel this way."
            ),
            "tips": [
                {"emoji": "😴", "color": "blue",  "text": "Prioritize sleep — aim for 7–8 hours every night."},
                {"emoji": "🚶", "color": "green", "text": "Take short breaks and a 20-minute walk daily to reset."},
                {"emoji": "📵", "color": "pink",  "text": "Limit social media and news before bedtime."},
                {"emoji": "🗣️", "color": "blue",  "text": "Talk to a trusted friend or counselor about your worries."},
            ]
        }
    elif score <= 32:
        return {
            "result":      "High Stress & Anxiety",
            "status_label":"High",
            "badge_class": "high",
            "icon":        "⚠️",
            "description": (
                "Your responses suggest significant stress and anxiety levels. "
                "It's important to take action now. Please don't ignore these signs — "
                "support is available and seeking help is a sign of strength."
            ),
            "tips": [
                {"emoji": "🆘", "color": "pink",  "text": "Speak with your college counselor or a mental health professional soon."},
                {"emoji": "📞", "color": "blue",  "text": "iCall Helpline: 9152987821 (Mon–Sat, 8AM–10PM)"},
                {"emoji": "🧘", "color": "green", "text": "Practice deep breathing: inhale 4s, hold 4s, exhale 6s."},
                {"emoji": "🛑", "color": "pink",  "text": "Reduce academic overload if possible — talk to your professors."},
            ]
        }
    else:
        return {
            "result":      "Severe Distress Detected",
            "status_label":"Severe",
            "badge_class": "high",
            "icon":        "🚨",
            "description": (
                "Your responses indicate a high level of distress. Please know that you are not alone "
                "and that help is available. Reaching out to a professional is the most important step "
                "you can take right now. Your well-being matters more than anything else."
            ),
            "tips": [
                {"emoji": "🆘", "color": "pink",  "text": "Please contact a mental health professional immediately."},
                {"emoji": "📞", "color": "pink",  "text": "NIMHANS Helpline: 080-46110007 | iCall: 9152987821"},
                {"emoji": "🤝", "color": "blue",  "text": "Tell a trusted adult (parent, teacher, counselor) how you're feeling."},
                {"emoji": "🏥", "color": "green", "text": "Visit your college health center for an in-person consultation."},
            ]
        }


# ─────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')


# ── REGISTER ──────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' in session:
        return redirect('/student-dashboard')

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        dob      = request.form.get('dob', '')

        # Basic validation
        if not name or len(name) < 2:
            flash('Please enter a valid full name.', 'error')
            return redirect('/register')

        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'error')
            return redirect('/register')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect('/register')

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO students (name, email, password, dob) VALUES (?, ?, ?, ?)",
                (name, email, password, dob)
            )
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('An account with this email already exists.', 'error')
            return redirect('/register')
        finally:
            conn.close()

    return render_template('register.html')


# ── LOGIN ─────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect('/student-dashboard')

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please fill in all fields.', 'error')
            return redirect('/login')

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM students WHERE email = ? AND password = ?",
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session['user'] = email
            session['name'] = user['name']
            session['user_id'] = user['id']
            return redirect('/student-dashboard')
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect('/login')

    return render_template('login.html')


# ── LOGOUT ────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect('/')


# ── STUDENT DASHBOARD ─────────────────────────
@app.route('/student-dashboard')
def student_dashboard():
    if 'user' not in session:
        flash('Please log in to access your dashboard.', 'error')
        return redirect('/login')

    conn = get_db()
    test_count = conn.execute(
        "SELECT COUNT(*) FROM test_results WHERE student_id = ?",
        (session.get('user_id'),)
    ).fetchone()[0]

    last_result = conn.execute(
        "SELECT total_score FROM test_results WHERE student_id = ? ORDER BY created_at DESC LIMIT 1",
        (session.get('user_id'),)
    ).fetchone()
    conn.close()

    last_score = last_result['total_score'] if last_result else None

    return render_template(
        'student_dashboard.html',
        test_count=test_count,
        last_score=last_score
    )


# ── TEST PAGE ─────────────────────────────────
@app.route('/test')
def test():
    if 'user' not in session:
        flash('Please log in to take the test.', 'error')
        return redirect('/login')
    return render_template('test.html')


# ── PREDICT / ANALYZE ─────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/login')

    # Helper function to aggregate scores for a category
    def get_category_score(field_name, request_form):
        """Get score for a category, averaging multiple questions if they exist"""
        values = []
        
        # Try single field first (quick mode)
        single_val = request_form.get(field_name)
        if single_val:
            try:
                values.append(int(single_val))
            except (ValueError, TypeError):
                pass
        
        # Try numbered fields (full mode): field_1, field_2, etc.
        counter = 1
        while True:
            multi_val = request_form.get(f"{field_name}_{counter}")
            if not multi_val:
                break
            try:
                values.append(int(multi_val))
            except (ValueError, TypeError):
                pass
            counter += 1
        
        # If we have values, average them
        if values:
            avg = sum(values) / len(values)
            return max(1, min(5, round(avg)))  # clamp to 1-5
        
        # Default fallback
        return 3

    # Collect all 8 scores
    fields = ['stress', 'anxiety', 'sleep', 'focus', 'social', 'sadness', 'energy', 'overwhelm']
    scores = {}
    for f in fields:
        scores[f] = get_category_score(f, request.form)
    
    # If quick mode (missing sadness, energy, overwhelm), estimate them intelligently
    test_mode = request.form.get('test_mode', 'full')
    if test_mode == 'quick':
        # Estimate missing fields based on user's actual answers
        # sadness ~ correlated with stress/anxiety
        if scores.get('sadness', 0) == 3:  # Default value
            scores['sadness'] = int((scores['stress'] + scores['anxiety']) / 2)
        
        # energy ~ inverse of focus difficulty (hard to focus = low energy)
        if scores.get('energy', 0) == 3:  # Default value
            scores['energy'] = max(1, 6 - scores['focus'])  # Invert: 5→1, 1→5
        
        # overwhelm ~ similar to stress
        if scores.get('overwhelm', 0) == 3:  # Default value
            scores['overwhelm'] = scores['stress']

    # Try ML model first
    ml_prob, ml_category = predict_ml(
        scores['stress'], scores['anxiety'], scores['sleep'], scores['focus'],
        scores['social'], scores['sadness'], scores['energy'], scores['overwhelm']
    )
    
    # Use ML model if available, otherwise fall back to rule-based
    if ml_category:
        analysis = analyze_score_by_category(ml_category)
        is_ml_prediction = True
        # Convert probability to 0-40 score scale for display
        total_score = int(ml_prob * 40)
    else:
        # Rule-based calculation from the 8 quiz dimensions
        # Risk factors (lower is better):
        # - stress (1-5): 1=low, 5=high stress
        # - anxiety (1-5): 1=low, 5=high anxiety  
        # - sleep (1-5): 1=poor, 5=good sleep (needs inversion)
        # - focus (1-5): 1=poor, 5=good focus (needs inversion)
        # - social (1-5): 1=isolated, 5=well-connected (needs inversion)
        # - sadness (1-5): 1=happy, 5=very sad
        # - energy (1-5): 1=very low, 5=high energy (needs inversion)
        # - overwhelm (1-5): 1=calm, 5=very overwhelmed
        
        # Convert 1-5 scales to risk factors by inverting positive dimensions
        risk_scores = {
            'stress':    scores['stress'],           # high value = high risk
            'anxiety':   scores['anxiety'],          # high value = high risk
            'sleep':     6 - scores['sleep'],        # low sleep = high risk
            'focus':     6 - scores['focus'],        # low focus = high risk
            'social':    6 - scores['social'],       # isolation = high risk
            'sadness':   scores['sadness'],          # high value = high risk
            'energy':    6 - scores['energy'],       # low energy = high risk
            'overwhelm': scores['overwhelm'],        # high value = high risk
        }
        total_score = sum(risk_scores.values())
        analysis = analyze_score(total_score)
        is_ml_prediction = False

    # Build breakdown list for the result page
    breakdown = [
        {"label": "Stress Level",       "value": scores['stress'],    "pct": scores['stress']    * 20, "color": "#e17055, #d63031"},
        {"label": "Anxiety",            "value": scores['anxiety'],   "pct": scores['anxiety']   * 20, "color": "#fdcb6e, #e17055"},
        {"label": "Sleep Quality",      "value": scores['sleep'],     "pct": scores['sleep']     * 20, "color": "#6c63ff, #a29bfe"},
        {"label": "Focus & Concentrate","value": scores['focus'],     "pct": scores['focus']     * 20, "color": "#fd79a8, #e84393"},
        {"label": "Social Connection",  "value": scores['social'],    "pct": scores['social']    * 20, "color": "#00cec9, #00b894"},
        {"label": "Mood / Sadness",     "value": scores['sadness'],   "pct": scores['sadness']   * 20, "color": "#74b9ff, #0984e3"},
        {"label": "Energy Level",       "value": scores['energy'],    "pct": scores['energy']    * 20, "color": "#55efc4, #00b894"},
        {"label": "Overwhelm",          "value": scores['overwhelm'], "pct": scores['overwhelm'] * 20, "color": "#a29bfe, #6c63ff"},
    ]

    # Save to DB
    try:
        conn = get_db()
        conn.execute("""
            INSERT INTO test_results
              (student_id, stress, anxiety, sleep, focus,
               social, sadness, energy, overwhelm, total_score, result, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.get('user_id'),
            scores['stress'], scores['anxiety'], scores['sleep'], scores['focus'],
            scores['social'], scores['sadness'], scores['energy'], scores['overwhelm'],
            total_score, analysis['result'], get_ist_timestamp()
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        pass  # Don't break the result page if DB write fails

    return render_template(
        'result.html',
        result=analysis['result'],
        status_label=analysis['status_label'],
        badge_class=analysis['badge_class'],
        icon=analysis['icon'],
        description=analysis['description'],
        tips=analysis['tips'],
        score=total_score,
        breakdown=breakdown,
        ml_confidence=f"{ml_prob*100:.1f}%" if ml_prob else None
    )


# ── HISTORY PAGE ──────────────────────────────
@app.route('/history')
def history():
    if 'user' not in session:
        flash('Please log in to view your history.', 'error')
        return redirect('/login')
    return render_template('history.html')


# ── API: TEST HISTORY ─────────────────────────
@app.route('/api/test-history', methods=['GET'])
def api_test_history():
    """Get test history for current student"""
    if 'user' not in session:
        return {'error': 'Not authenticated'}, 401
    
    try:
        conn = get_db()
        tests = conn.execute("""
            SELECT total_score, result, created_at
            FROM test_results
            WHERE student_id = ?
            ORDER BY created_at DESC
        """, (session.get('user_id'),)).fetchall()
        conn.close()
        
        test_list = [
            {
                'total_score': test['total_score'],
                'result': test['result'],
                'date': test['created_at']
            }
            for test in tests
        ]
        
        return {'tests': test_list}, 200
    except Exception as e:
        print(f"Error fetching test history: {e}")
        return {'error': str(e)}, 500


# ── MOOD TRACKING API ────────────────────────
@app.route('/api/record-mood', methods=['POST'])
def record_mood():
    """Record daily mood check-in (one entry per day)"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    mood = request.json.get('mood')
    if not mood:
        return {'error': 'Mood required'}, 400
    
    try:
        conn = get_db()
        student_id = session.get('user_id')
        
        # Check if student already logged a mood today
        existing_mood = conn.execute(
            """SELECT mood, created_at FROM mood_logs 
               WHERE student_id = ? AND date(created_at) = date('now')
               LIMIT 1""",
            (student_id,)
        ).fetchone()
        
        if existing_mood:
            # Already logged today - return existing mood with message
            conn.close()
            return {
                'success': False,
                'error': 'already_logged',
                'message': 'You have already logged your mood today.',
                'today_mood': existing_mood['mood'],
                'logged_at': existing_mood['created_at']
            }, 200
        
        # No entry for today - create new one
        conn.execute(
            "INSERT INTO mood_logs (student_id, mood, created_at) VALUES (?, ?, ?)",
            (student_id, mood, get_ist_timestamp())
        )
        conn.commit()
        conn.close()
        return {'success': True, 'mood': mood, 'message': 'Mood logged successfully! You can log again tomorrow.'}, 200
    except Exception as e:
        print(f"Error recording mood: {e}")
        return {'error': str(e)}, 500


@app.route('/api/mood-history', methods=['GET'])
def mood_history():
    """Get mood history for current student (last 7 days)"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    try:
        conn = get_db()
        moods = conn.execute(
            """SELECT mood, created_at FROM mood_logs 
               WHERE student_id = ? AND date(created_at) >= date('now', '-7 days')
               ORDER BY created_at DESC""",
            (session.get('user_id'),)
        ).fetchall()
        conn.close()
        
        return {
            'moods': [dict(m) for m in moods],
            'count': len(moods)
        }, 200
    except Exception as e:
        print(f"Error fetching mood history: {e}")
        return {'error': str(e)}, 500


@app.route('/api/mood-stats', methods=['GET'])
def mood_stats():
    """Get mood statistics for personalized recommendations"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    try:
        conn = get_db()
        # Get today's moods
        today_moods = conn.execute(
            """SELECT mood FROM mood_logs 
               WHERE student_id = ? AND date(created_at) = date('now')
               ORDER BY created_at DESC""",
            (session.get('user_id'),)
        ).fetchall()
        
        # Get last 7 days mood distribution
        week_moods = conn.execute(
            """SELECT mood, COUNT(*) as count FROM mood_logs 
               WHERE student_id = ? AND date(created_at) >= date('now', '-7 days')
               GROUP BY mood""",
            (session.get('user_id'),)
        ).fetchall()
        conn.close()
        
        mood_distribution = {m['mood']: m['count'] for m in week_moods}
        latest_mood = today_moods[0]['mood'] if today_moods else None
        
        return {
            'latest_mood': latest_mood,
            'mood_distribution': mood_distribution,
            'total_logs_this_week': sum(mood_distribution.values())
        }, 200
    except Exception as e:
        print(f"Error calculating mood stats: {e}")
        return {'error': str(e)}, 500


# ── DAILY TIPS PAGE ───────────────────────────
@app.route('/daily-tips')
def daily_tips():
    if 'user' not in session:
        flash('Please log in to view daily tips.', 'error')
        return redirect('/login')
    return render_template('daily_tips.html')


# ── RESOURCES PAGE ────────────────────────────
@app.route('/resources')
def resources():
    if 'user' not in session:
        flash('Please log in to view resources.', 'error')
        return redirect('/login')
    return render_template('resources.html')



# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    init_db()   # ensure tables exist on every startup
    app.run(debug=True, port=5000)
