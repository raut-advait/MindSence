from flask import Flask, render_template, request, redirect, session, flash, jsonify
import os
import logging
import re
import numpy as np
import joblib
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List

try:
    from groq import Groq
except Exception:
    Groq = None

# Import optimized database helpers
from db_helpers import (
    init_db, get_db_connection, get_ist_timestamp,
    create_student, get_student, get_student_by_email, update_student,
    create_quick_assessment, get_quick_assessment, get_quick_assessments,
    get_latest_quick_assessment, create_full_assessment, get_full_assessment,
    get_full_assessments, get_latest_full_assessment, record_mood,
    get_mood_history, get_mood_stats, get_student_dashboard_stats,
    get_all_students_aggregate_stats
)

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('mental_health_app')


def _load_local_env(file_name: str = '.env.local') -> None:
    env_path = Path(__file__).resolve().parent / file_name
    if not env_path.exists():
        return

    try:
        for raw_line in env_path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception as exc:
        logger.warning('Could not load %s: %s', env_path, exc)


_load_local_env()

GROQ_MODEL = os.environ.get('GROQ_MODEL', 'llama-3.1-8b-instant')


def _llm_api_key() -> str:
    return (os.environ.get('GROQ_API_KEY') or '').strip()


def _is_llm_ready() -> bool:
    return bool(Groq is not None and _llm_api_key())


def _call_llm(system_prompt: str, user_prompt: str, max_output_tokens: int = 350) -> str:
    if not _is_llm_ready():
        return "AI assistant is not configured yet. Please set GROQ_API_KEY on the server."

    try:
        client = Groq(api_key=_llm_api_key())
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.4,
            max_tokens=max_output_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = ((response.choices[0].message.content if response.choices else "") or "").strip()
        return text or "I couldn't generate a response right now."
    except Exception as exc:
        logger.error("Groq call failed: %s - %s", type(exc).__name__, exc, exc_info=True)
        error_text = str(exc).lower()
        if 'authentication' in error_text or 'invalid api key' in error_text or '401' in error_text:
            return "Invalid GROQ_API_KEY. Please update .env.local with a valid Groq key and restart the server."
        return f"AI service error: {type(exc).__name__}: {str(exc)[:100]}"


def _build_student_analytics_payload(student_id: int) -> Dict:
    quick = get_quick_assessments(student_id, limit=40)
    full = get_full_assessments(student_id, limit=40)
    moods = get_mood_history(student_id, days=14)

    merged: List[Dict] = []
    for item in quick:
        merged.append({
            "type": "quick",
            "score": item.get("total_score"),
            "result": item.get("result_category"),
            "created_at": str(item.get("created_at")),
        })
    for item in full:
        merged.append({
            "type": "full",
            "score": item.get("total_score"),
            "result": item.get("result_category"),
            "ml_probability": item.get("ml_probability"),
            "created_at": str(item.get("created_at")),
        })
    merged.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    result_counts: Dict[str, int] = {}
    for item in merged:
        key = item.get("result") or "Unknown"
        result_counts[key] = result_counts.get(key, 0) + 1

    mood_counts: Dict[str, int] = {}
    for mood in moods:
        key = mood.get("mood") or "Unknown"
        mood_counts[key] = mood_counts.get(key, 0) + 1

    return {
        "total_assessments": len(merged),
        "latest": merged[:10],
        "result_counts": result_counts,
        "mood_counts": mood_counts,
    }

# Flask app instance
app = Flask(__name__, template_folder='templates', static_folder='static')
# Secret key for sessions (override via env var in production)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

try:
    init_db()
    logger.info("Database initialized")
except Exception as exc:
    logger.error("Database initialization failed: %s", exc)

# Indian Standard Time (IST) timezone
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_timestamp():
    """Return current timestamp in Indian Standard Time (IST)."""
    return datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')


def validate_quiz_input(value, field_name: str, min_val: int = 1, max_val: int = 5) -> int:
    """
    Validate and clamp a single quiz field value.

    Ensures the value is a valid integer in [min_val, max_val].
    Falls back to the midpoint if the value is missing or invalid.

    Args:
        value: Raw value from request.form
        field_name: Name of the field (used in log messages)
        min_val: Minimum accepted value (default 1)
        max_val: Maximum accepted value (default 5)

    Returns:
        int in [min_val, max_val]
    """
    default = (min_val + max_val) // 2
    if value is None or value == '':
        logger.warning("Missing quiz field '%s', using default %d", field_name, default)
        return default
    try:
        v = int(float(value))
    except (ValueError, TypeError):
        logger.warning("Invalid value '%s' for field '%s', using default %d", value, field_name, default)
        return default
    if not (min_val <= v <= max_val):
        clamped = max(min_val, min(max_val, v))
        logger.warning("Out-of-range value %d for '%s', clamped to %d", v, field_name, clamped)
        return clamped
    return v


# ─────────────────────────────────────────────────────────────────────────────
# LOAD FINAL BINARY MODEL  (v5.0-binary, CalibratedClassifierCV)
# ─────────────────────────────────────────────────────────────────────────────

def _load_ml_components():
    """Legacy binary model disabled; lifestyle model is the active predictor."""
    return None, None, []


# ─────────────────────────────────────────────────────────────────────────────
# LOAD LIFESTYLE MODEL (gradient boosting from student_lifestyle_100k.csv)
# ─────────────────────────────────────────────────────────────────────────────

def _load_lifestyle_components():
    """Load lifestyle preprocessor, classifier, metadata, and feature list."""
    try:
        pre = joblib.load('models/preprocessor.pkl')
        clf = joblib.load('models/trained_model.pkl')
        # ensure preprocessor has feature names for dataframe transformations
        try:
            if hasattr(pre, 'feature_names_in_') and getattr(pre, '_feature_names_in', None) is None:
                pre._feature_names_in = pre.feature_names_in_
        except Exception:
            pass
        with open('models/metadata.json', 'r', encoding='utf-8') as fh:
            meta = json.load(fh)
        # load feature names separately (not stored in metadata)
        feat_meta = {}
        try:
            with open('models/features.json', 'r', encoding='utf-8') as fh:
                feat_meta = json.load(fh)
        except Exception:
            pass
        # merge for convenience
        meta = {**meta, **feat_meta}
        return pre, clf, meta
    except Exception as exc:
        logger.error("Failed to load lifestyle components: %s", exc)
        return None, None, None


# Loaded once at startup
_ml_model, _ml_scaler, _ml_feature_names = _load_ml_components()
if _ml_model is not None:
    logger.info("ML model loaded — final_model.pkl (binary v5.0)")
else:
    logger.info("Legacy binary model disabled — using lifestyle model pipeline")

# lifestyle model globals
_lifestyle_pre, _lifestyle_model, _lifestyle_meta = _load_lifestyle_components()
if _lifestyle_model is not None:
    logger.info("Lifestyle model loaded — trained_model.pkl")
else:
    logger.warning("Lifestyle model unavailable — lifestyle predictions disabled")


# ─────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────




def predict_ml(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm):
    """
    Mental health risk scorer — rule-based primary, ML model referenced.

    PRIMARY: Weighted rule-based scorer across all 8 quiz dimensions.
    The trained ML model (final_model.pkl, v5.0-binary) is loaded and its
    P(High Risk) is computed for logging/documentation, but it does NOT
    drive the UI result because the model outputs near-constant ~0.23 for
    all inputs (ROC-AUC = 0.517, below useful discrimination threshold).

    Rule-based weights:
        Risk dimensions   (stress, anxiety, sadness, overwhelm)  → weight 1.5
        Protective dims   (sleep, focus, social, energy)         → weight 1.0
        Both on 1–5 quiz scale; protective dimensions inverted.

    UI probability → category (locked architecture):
        0.00–0.25  → Excellent Mental Well-being
        0.25–0.50  → Moderate Stress Detected
        0.50–0.75  → High Stress & Anxiety
        0.75–1.00  → Severe Distress Detected

    Returns:
        (probability: float 0–1, category: str)
    """
    # ── Rule-based primary scorer ─────────────────────────────────────────────
    s   = float(stress);  a   = float(anxiety)
    sl  = float(sleep);   fo  = float(focus)
    so  = float(social);  sad = float(sadness)
    en  = float(energy);  ov  = float(overwhelm)

    rw, pw = 1.5, 1.0
    raw   = rw*s + rw*a + rw*sad + rw*ov + pw*(6-sl) + pw*(6-fo) + pw*(6-so) + pw*(6-en)
    min_r = 4 * rw * 1 + 4 * pw * 1   # best case  = 10.0
    max_r = 4 * rw * 5 + 4 * pw * 5   # worst case = 50.0
    probability = max(0.0, min(1.0, (raw - min_r) / (max_r - min_r)))

    if probability < 0.25:      category = "Excellent Mental Well-being"
    elif probability < 0.50:    category = "Moderate Stress Detected"
    elif probability < 0.75:    category = "High Stress & Anxiety"
    else:                       category = "Severe Distress Detected"

    # ── ML model — informational only (log P(High Risk) for documentation) ────
    if _ml_model is not None and _ml_scaler is not None:
        try:
            activity_val = (float(focus) + float(energy)) / 2.0
            feature_values = {
                'stress':           s,
                'anxiety':          a,
                'sleep':            sl,
                'activity':         activity_val,
                'social':           so,
                'financial_stress': 2.5,
                'counseling':       0.0,
                'family_history':   0.0,
                'chronic_illness':  0.0,
            }
            # Pass DataFrame — scaler was fitted on DataFrame in train_model.py
            X_df = pd.DataFrame([feature_values], columns=_ml_feature_names)
            X_scaled = _ml_scaler.transform(X_df)
            ml_prob = float(_ml_model.predict_proba(X_scaled)[0][1])
            logger.info("ML P(High Risk)=%.4f | Rule-based risk=%.4f | Result: %s",
                        ml_prob, probability, category)
        except Exception as exc:
            logger.debug("ML informational query failed: %s", exc)

    return probability, category



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
#  FALLBACK RULE-BASED SCORING
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
        name       = request.form.get('name', '').strip()
        email      = request.form.get('email', '').strip().lower()
        password   = request.form.get('password', '')
        dob        = request.form.get('dob', '')
        # profile fields moved to signup
        age        = request.form.get('age')
        gender     = request.form.get('gender')
        department = request.form.get('department', '').strip()
        academic_year = request.form.get('academic_year', '').strip()
        cgpa       = request.form.get('cgpa')

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

        # Create student using optimized helper
        student_id = create_student(
            name=name,
            email=email,
            password=password,
            dob=dob,
            age=int(age) if age else None,
            gender=gender,
            department=department,
            academic_year=academic_year,
            cgpa=float(cgpa) if cgpa else None
        )
        
        if student_id:
            flash('Account created successfully! Please log in.', 'success')
            return redirect('/login')
        else:
            flash('An account with this email already exists.', 'error')
            return redirect('/register')

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

        user = get_student_by_email(email)

        if user and user.get('password') == password:
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

    # Get comprehensive dashboard stats
    stats = get_student_dashboard_stats(session.get('user_id'))
    
    total_tests = stats['quick_assessments'] + stats['full_assessments']
    last_score = None
    last_category = None
    
    if stats['latest_quick']:
        last_score = stats['latest_quick']['total_score']
        last_category = stats['latest_quick']['result_category']
    elif stats['latest_full']:
        last_score = stats['latest_full']['total_score']
        last_category = stats['latest_full']['result_category']

    return render_template(
        'student_dashboard.html',
        test_count=total_tests,
        last_score=last_score,
        last_category=last_category,
        quick_count=stats['quick_assessments'],
        full_count=stats['full_assessments'],
        avg_30day_score=stats['avg_score_30days']
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
    global _lifestyle_pre, _lifestyle_model, _lifestyle_meta

    if 'user' not in session:
        return redirect('/login')

    assessment_mode = (request.form.get('mode', 'quick') or 'quick').strip().lower()

    if _lifestyle_model is None:
        _lifestyle_pre, _lifestyle_model, _lifestyle_meta = _load_lifestyle_components()
        if _lifestyle_model is None:
            logger.warning("Lifestyle model not available at request time; using rule-based fallback")

    # load basic profile info (for academic tips)
    profile = {}
    if session.get('user_id'):
        try:
            student = get_student(session.get('user_id'))
            if student:
                profile = {
                    'age': student.get('age'),
                    'gender': student.get('gender'),
                    'department': student.get('department'),
                    'cgpa': student.get('cgpa'),
                }
        except Exception:
            profile = {}

    def _clamp_1_5(value, default=3):
        try:
            return int(max(1, min(5, round(float(value)))))
        except Exception:
            return int(default)

    def _sleep_hours_to_quality(hours):
        try:
            h = float(hours)
        except Exception:
            return 3
        if h <= 4:
            return 1
        if h <= 6:
            return 2
        if h <= 7:
            return 3
        if h <= 8:
            return 4
        return 5

    def _scores_from_lifestyle_form(form):
        stress = _clamp_1_5(form.get('Stress_Level', 3), 3)
        anxiety = _clamp_1_5(form.get('Anxiety_Level', stress), stress)
        sleep_quality = _sleep_hours_to_quality(form.get('Sleep_Duration', 7))
        focus = _clamp_1_5(form.get('Focus_Level', 3), 3)
        social = _clamp_1_5(form.get('Social_Support', 3), 3)

        sadness_default = max(1, min(5, round((stress + anxiety) / 2)))
        sadness = _clamp_1_5(form.get('Sadness_Level', sadness_default), sadness_default)

        energy_default = 3
        try:
            activity_hours = float(form.get('Physical_Activity', 1.5))
            if activity_hours <= 0.5:
                energy_default = 2
            elif activity_hours <= 1.5:
                energy_default = 3
            elif activity_hours <= 2.5:
                energy_default = 4
            else:
                energy_default = 5
        except Exception:
            pass
        energy = _clamp_1_5(form.get('Energy_Level', energy_default), energy_default)

        overwhelm_default = max(1, min(5, round((stress + anxiety + sadness) / 3)))
        overwhelm = _clamp_1_5(form.get('Overwhelm_Level', overwhelm_default), overwhelm_default)

        return {
            'stress': stress,
            'anxiety': anxiety,
            'sleep': sleep_quality,
            'focus': focus,
            'social': social,
            'sadness': sadness,
            'energy': energy,
            'overwhelm': overwhelm,
        }

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

    # lifestyle model branch: run only for explicit FULL mode submissions
    if _lifestyle_model is not None and assessment_mode == 'full' and 'Sleep_Duration' in request.form:
        # build record from form & optional profile
        feats = []
        feats.extend(_lifestyle_meta.get('numeric_features', []))
        feats.extend(_lifestyle_meta.get('categorical_features', []))
        rec = {}
        for feat in feats:
            val = request.form.get(feat)
            if val is None:
                rec[feat] = np.nan
            else:
                try:
                    rec[feat] = float(val)
                except ValueError:
                    rec[feat] = val
        # pull stored profile values if missing
        user_id = session.get('user_id')
        if user_id:
            try:
                student = get_student(user_id)
                if student:
                    if pd.isna(rec.get('Age', np.nan)) and student.get('age') is not None:
                        rec['Age'] = student.get('age')
                    if pd.isna(rec.get('Gender', np.nan)) and student.get('gender') is not None:
                        rec['Gender'] = student.get('gender')
                    if pd.isna(rec.get('Department', np.nan)) and student.get('department') is not None:
                        rec['Department'] = student.get('department')
                    if pd.isna(rec.get('CGPA', np.nan)) and student.get('cgpa') is not None:
                        rec['CGPA'] = student.get('cgpa')
            except Exception:
                pass
        # use the trained lifestyle model to score submitted answers
        mode = assessment_mode

        # helper to safely read numeric values from rec or request.form
        def _safe_float(key, default):
            try:
                v = rec.get(key, np.nan)
                if pd.isna(v):
                    v = request.form.get(key)
                if v is None:
                    return float(default)
                return float(v)
            except Exception:
                return float(default)

        stress_val = _safe_float('Stress_Level', 3.0)
        sleep = _safe_float('Sleep_Duration', 7)
        study = _safe_float('Study_Hours', 3)
        activity = _safe_float('Physical_Activity', 1)

        # additional full-survey fields (1-5 scales)
        anxiety = _safe_float('Anxiety_Level', 3)
        focus = _safe_float('Focus_Level', 3)
        social_conn = _safe_float('Social_Support', 3)
        sadness = _safe_float('Sadness_Level', 3)
        energy = _safe_float('Energy_Level', 3)
        overwhelm = _safe_float('Overwhelm_Level', 3)

        # fill missing core model features with stable defaults
        rec.setdefault('Age', 21)
        rec.setdefault('Gender', 'Other')
        rec.setdefault('Department', 'General')
        rec.setdefault('CGPA', 3.0)
        rec.setdefault('Sleep_Duration', sleep)
        rec.setdefault('Study_Hours', study)
        rec.setdefault('Social_Media', _safe_float('Social_Media', 2.0))
        rec.setdefault('Physical_Activity', activity)
        rec.setdefault('Stress_Level', stress_val)

        # Recreate engineered features expected by the trained lifestyle model.
        # Training script uses these derived columns; missing them at inference
        # pushes predictions toward a single class.
        def _norm(value, min_v, max_v):
            try:
                v = float(value)
            except Exception:
                v = float(min_v)
            if max_v <= min_v:
                return 0.0
            v = max(min_v, min(max_v, v))
            return (v - min_v) / (max_v - min_v)

        sleep_val = float(rec.get('Sleep_Duration', sleep))
        study_val = float(rec.get('Study_Hours', study))
        social_media_val = float(rec.get('Social_Media', 2.0))
        activity_val = float(rec.get('Physical_Activity', activity))
        stress_model_val = float(rec.get('Stress_Level', stress_val))
        cgpa_val = float(rec.get('CGPA', 3.0))

        rec['sleep_study_ratio'] = sleep_val / (study_val + 1.0)
        social_norm = _norm(social_media_val, 0.0, 6.0)
        physical_norm = _norm(activity_val, 0.0, 3.5)
        rec['social_activity_score'] = 0.6 * physical_norm + 0.4 * (1.0 - social_norm)
        study_norm = _norm(study_val, 0.0, 7.0)
        stress_norm = _norm(stress_model_val, 1.0, 5.0)
        cgpa_norm = _norm(cgpa_val, 0.0, 10.0)
        rec['academic_stress_index'] = 0.4 * study_norm + 0.4 * stress_norm + 0.2 * (1.0 - cgpa_norm)
        rec['stress_x_sleep'] = stress_model_val * sleep_val
        rec['study_x_stress'] = study_val * stress_model_val
        rec['cgpa_x_stress'] = cgpa_val * stress_model_val

        # Ensure model feature order matches training
        model_features = []
        model_features.extend(_lifestyle_meta.get('numeric_features', []))
        model_features.extend(_lifestyle_meta.get('categorical_features', []))

        try:
            model_row = {}
            for feat in model_features:
                if feat in ('Gender', 'Department'):
                    model_row[feat] = str(rec.get(feat, 'Unknown'))
                else:
                    model_row[feat] = float(rec.get(feat, 0.0))

            X_row = pd.DataFrame([model_row], columns=model_features)
            prob = float(_lifestyle_model.predict_proba(X_row)[0][1])
            threshold = float(_lifestyle_meta.get('selected_threshold', 0.5))
            threshold = min(max(threshold, 0.05), 0.50)

            # Convert probability to a score relative to the model's own decision threshold.
            # At threshold -> score ~10/40, then rising with increasing confidence.
            total_score = int(round((prob / threshold) * 10.0))
            total_score = min(max(total_score, 0), 40)

            # Threshold-aware risk bands (aligned with selected_threshold from metadata).
            # Use tighter boundaries to avoid over-labeling "Excellent".
            excellent_cut = min(1.0, threshold * 0.45)
            moderate_cut = min(1.0, threshold * 0.90)
            high_cut = min(1.0, threshold * 1.35)

            if prob < excellent_cut:
                ml_category = "Excellent Mental Well-being"
                band = "Excellent"
            elif prob < moderate_cut:
                ml_category = "Moderate Stress Detected"
                band = "Moderate"
            elif prob < high_cut:
                ml_category = "High Stress & Anxiety"
                band = "High"
            else:
                ml_category = "Severe Distress Detected"
                band = "Severe"

            analysis = analyze_score_by_category(ml_category)
            logger.info(
                "Lifestyle model prediction | mode=%s | P(Depression)=%.4f | threshold=%.3f | score=%d | band=%s",
                mode, prob, threshold, total_score, band
            )
        except Exception as exc:
            logger.error("Lifestyle model prediction failed, falling back to rule-based scoring: %s", exc)
            fallback_scores = _scores_from_lifestyle_form(request.form)
            risk_scores = {
                'stress':    fallback_scores['stress'],
                'anxiety':   fallback_scores['anxiety'],
                'sleep':     6 - fallback_scores['sleep'],
                'focus':     6 - fallback_scores['focus'],
                'social':    6 - fallback_scores['social'],
                'sadness':   fallback_scores['sadness'],
                'energy':    6 - fallback_scores['energy'],
                'overwhelm': fallback_scores['overwhelm'],
            }
            total_score = int(sum(risk_scores.values()))
            analysis = analyze_score(total_score)
            prob = None
            threshold = None
            band = None
        # supplement analysis with profile/activity specific tips
        extra_tips = []
        if profile.get('cgpa') is not None:
            try:
                cgpa_val = float(profile.get('cgpa'))
                if cgpa_val < 7.0:
                    extra_tips.append({
                        "emoji": "📚", "color": "blue",
                        "text": f"Your CGPA is {cgpa_val:.1f}. Consider creating a study plan or using tutoring resources to improve."})
                else:
                    extra_tips.append({
                        "emoji": "🎓", "color": "green",
                        "text": f"Your CGPA is {cgpa_val:.1f}. Keep maintaining your strong academic performance!"})
            except Exception:
                pass
        try:
            act = float(rec.get('Physical_Activity', 0))
            if act < 1.0:
                extra_tips.append({
                    "emoji": "🏃", "color": "green",
                    "text": "Try to get at least 30 minutes of moderate exercise a few times this week to boost mood."})
        except Exception:
            pass
        if extra_tips:
            analysis['tips'].extend(extra_tips)

        is_ml_prediction = False
        display_score = total_score    # show the calculated score on the gauge
        # prob/threshold/band are set above by the model branch
        # provide a breakdown so users can see inputs (expanded for full survey)
        social_media_val = rec.get('Social_Media', None)
        breakdown = [
            {"label": "Stress Level", "value": stress_val,
             "pct": (stress_val or 0) / 5.0 * 100, "color": "#e17055, #d63031"},
            {"label": "Anxiety", "value": anxiety,
             "pct": (anxiety or 0) * 20, "color": "#fdcb6e, #e17055"},
            {"label": "Mood / Sadness", "value": sadness,
             "pct": (sadness or 0) * 20, "color": "#74b9ff, #0984e3"},
            {"label": "Sleep (hrs)", "value": sleep,
             "pct": min((sleep or 0) / 9.0 * 100, 100), "color": "#6c63ff, #a29bfe"},
            {"label": "Study (hrs)", "value": study,
             "pct": min((study or 0) / 8.0 * 100, 100), "color": "#fd79a8, #e84393"},
            {"label": "Social media (hrs)", "value": social_media_val,
             "pct": min((social_media_val or 0) / 6.0 * 100, 100), "color": "#00cec9, #00b894"},
            {"label": "Social Support", "value": social_conn,
             "pct": (social_conn or 0) * 20, "color": "#55efc4, #00b894"},
            {"label": "Physical activity (hrs)", "value": activity,
             "pct": min((activity or 0) / 3.5 * 100, 100), "color": "#55efc4, #00b894"},
            {"label": "Focus / Concentration", "value": focus,
             "pct": (focus or 0) * 20, "color": "#fd79a8, #e84393"},
            {"label": "Energy Level", "value": energy,
             "pct": (energy or 0) * 20, "color": "#a29bfe, #6c63ff"},
        ]

        stored_scores = {
            'stress': _clamp_1_5(stress_val),
            'anxiety': _clamp_1_5(anxiety),
            'sleep': _sleep_hours_to_quality(sleep),
            'focus': _clamp_1_5(focus),
            'social': _clamp_1_5(social_conn),
            'sadness': _clamp_1_5(sadness),
            'energy': _clamp_1_5(energy),
            'overwhelm': _clamp_1_5((stress_val + anxiety + sadness) / 3.0),
        }

        # save simplified result to database
        # Save as full assessment with ML features
        try:
            ml_features = {
                'stress_level': float(stress_val),
                'sleep_duration': float(sleep),
                'study_hours': float(study),
                'physical_activity': float(activity),
                'social_media': float(social_media_val) if social_media_val else 2.0
            }
            score_dims = {
                'anxiety': max(1, min(5, round(float(anxiety)))),
                'focus': max(1, min(5, round(float(focus)))),
                'social_support': max(1, min(5, round(float(social_conn)))),
                'sadness': max(1, min(5, round(float(sadness)))),
                'energy': max(1, min(5, round(float(energy)))),
                'overwhelm': max(1, min(5, round(float(overwhelm))))
            }
            create_full_assessment(
                student_id=session.get('user_id'),
                ml_features=ml_features,
                scores=score_dims,
                total_score=total_score,
                result_category=analysis['result'],
                ml_probability=prob,
                ml_threshold=threshold
            )
        except Exception as e:
            logger.error(f"Full assessment save failed: {e}")

        return render_template('result.html',
                       result=analysis['result'],
                       status_label=analysis.get('status_label'),
                       badge_class=analysis.get('badge_class'),
                       icon=analysis.get('icon'),
                       description=analysis.get('description'),
                       tips=analysis.get('tips'),
                       breakdown=breakdown,
                       total_score=total_score,
                       score=display_score,
                       is_ml_prediction=is_ml_prediction,
                       ml_probability=prob,
                       ml_threshold=threshold,
                       ml_band=band,
                       profile=profile)
        # if lifestyle model not loaded fall through to normal path

    # Collect all 8 scores
    fields = ['stress', 'anxiety', 'sleep', 'focus', 'social', 'sadness', 'energy', 'overwhelm']
    scores = {}

    if 'Sleep_Duration' in request.form:
        scores = _scores_from_lifestyle_form(request.form)
    else:
        for f in fields:
            scores[f] = get_category_score(f, request.form)
    
    # If quick mode (missing sadness, energy, overwhelm), estimate them intelligently
    test_mode = assessment_mode
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
    # Save as quick assessment
    try:
        if assessment_mode == 'quick':
            stored_quick_scores = {
                'stress': _clamp_1_5(request.form.get('Stress_Level', scores.get('stress', 3))),
                'anxiety': None,
                'sleep_quality': _sleep_hours_to_quality(request.form.get('Sleep_Duration', 7)),
                'focus': None,
                'social': None,
                'sadness': None,
                'energy': None,
                'overwhelm': None,
            }
        else:
            stored_quick_scores = {
                'stress': scores.get('stress'),
                'anxiety': scores.get('anxiety'),
                'sleep_quality': scores.get('sleep'),
                'focus': scores.get('focus'),
                'social': scores.get('social'),
                'sadness': scores.get('sadness'),
                'energy': scores.get('energy'),
                'overwhelm': scores.get('overwhelm'),
            }

        create_quick_assessment(
            student_id=session.get('user_id'),
            scores=stored_quick_scores,
            total_score=total_score,
            result_category=analysis['result']
        )
    except Exception as e:
        logger.error(f"Quick assessment save failed: {e}")

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
        ml_confidence=f"{ml_prob*100:.1f}%" if ml_prob else None,
        profile=profile
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
        student_id = session.get('user_id')
        student = get_student(student_id)
        
        # Get both quick and full assessments
        quick_tests = get_quick_assessments(student_id, limit=100)
        full_tests = get_full_assessments(student_id, limit=100)
        
        # Combine and sort by date descending
        all_tests = []
        for test in quick_tests:
            all_tests.append({
                'type': 'quick',
                'total_score': test['total_score'],
                'result': test['result_category'],
                'date': test['created_at'],
                'department': student.get('department', '') if student else '',
                'academic_year': student.get('academic_year', '') if student else ''
            })
        
        for test in full_tests:
            all_tests.append({
                'type': 'full',
                'total_score': test['total_score'],
                'result': test['result_category'],
                'date': test['created_at'],
                'ml_probability': test.get('ml_probability'),
                'department': student.get('department', '') if student else '',
                'academic_year': student.get('academic_year', '') if student else ''
            })
        
        # Sort by date, most recent first
        all_tests.sort(key=lambda x: x['date'], reverse=True)
        
        return {'tests': all_tests}, 200
    except Exception as e:
        logger.error(f"Error fetching test history: {e}")
        return {'error': str(e)}, 500


# ── MOOD TRACKING API ────────────────────────
@app.route('/api/record-mood', methods=['POST'])
def record_mood_endpoint():
    """Record daily mood check-in (one entry per day)"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    mood = request.json.get('mood')
    if not mood:
        return {'error': 'Mood required'}, 400
    
    note = request.json.get('note')
    success, message = record_mood(session.get('user_id'), mood, note)
    
    if success:
        return {'success': True, 'mood': mood, 'message': message}, 200
    else:
        lowered = (message or '').lower()
        if 'already logged' in lowered:
            return {'success': False, 'error': 'already_logged', 'message': message}, 200
        if 'invalid mood value' in lowered:
            return {'success': False, 'error': 'invalid_mood', 'message': 'Please select a valid mood option.'}, 400
        return {'success': False, 'error': 'save_failed', 'message': message}, 500


@app.route('/api/mood-history', methods=['GET'])
def mood_history_endpoint():
    """Get mood history for current student (last 7 days)"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    moods = get_mood_history(session.get('user_id'), days=7)
    return {
        'moods': moods,
        'count': len(moods)
    }, 200


@app.route('/api/mood-stats', methods=['GET'])
def mood_stats_endpoint():
    """Get mood statistics for personalized recommendations"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    stats = get_mood_stats(session.get('user_id'), days=7)
    return stats, 200


@app.route('/api/analytics-summary', methods=['POST'])
def analytics_summary_endpoint():
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401

    student_id = session.get('user_id')
    payload = _build_student_analytics_payload(student_id)

    system_prompt = (
        "You are MindSense analytics assistant. Provide a concise, supportive summary for a student. "
        "Do not diagnose. Do not mention self-harm instructions. "
        "Output exactly 5 short bullet points as plain text."
    )
    user_prompt = (
        "Create a personalized summary using this data:\n"
        f"{json.dumps(payload, default=str)}\n\n"
        "Include: trend insight, risk pattern, mood pattern, one practical suggestion, one encouragement line."
    )

    summary_text = _call_llm(system_prompt, user_prompt, max_output_tokens=280)
    return {'summary': summary_text}, 200


@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401

    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    history = data.get('history') or []

    if not message:
        return {'error': 'Message is required'}, 400

    if len(message) > 1200:
        return {'error': 'Message too long'}, 400

    danger_pattern = re.compile(r"\b(kill myself|suicide|self harm|end my life|hurt myself)\b", re.IGNORECASE)
    if danger_pattern.search(message):
        safe_reply = (
            "I’m really sorry you’re feeling this way. You deserve immediate support. "
            "Please contact local emergency services or a trusted person right now. "
            "If you're in India, you can call iCall 9152987821."
        )
        return {'reply': safe_reply}, 200

    trimmed_history = history[-6:] if isinstance(history, list) else []
    history_block = "\n".join(
        f"{('User' if item.get('role') == 'user' else 'Assistant')}: {item.get('content', '')}"
        for item in trimmed_history if isinstance(item, dict)
    )

    system_prompt = (
        "You are MindSense chat assistant. You help with two things only: "
        "(1) basic usage of this application, and (2) general mental wellness suggestions. "
        "Never provide diagnosis, prescriptions, or legal/medical certainty. "
        "If asked outside scope, politely redirect to app/help context. "
        "Keep responses short, friendly, and practical (3-6 lines)."
    )
    user_prompt = (
        f"Conversation so far:\n{history_block}\n\n"
        f"New user message:\n{message}\n\n"
        "Respond as assistant."
    )

    reply_text = _call_llm(system_prompt, user_prompt, max_output_tokens=320)
    return {'reply': reply_text}, 200


# ── MODEL INFO API ─────────────────────────────
@app.route('/api/model-info', methods=['GET'])
def model_info():
    """
    Return model metadata for transparency and debugging.
    Useful during viva demonstration to show model provenance.
    """
    if _lifestyle_model is None or _lifestyle_meta is None:
        return jsonify({'error': 'Model not loaded'}), 503

    numeric_features = _lifestyle_meta.get('numeric_features', [])
    categorical_features = _lifestyle_meta.get('categorical_features', [])
    feature_names = numeric_features + categorical_features

    info = {
        'model_type': _lifestyle_meta.get('model_type', 'Unknown'),
        'model_name': _lifestyle_meta.get('model_name', 'trained_model.pkl'),
        'version': _lifestyle_meta.get('version', 'lifestyle-current'),
        'target': _lifestyle_meta.get('target', 'depression_risk'),
        'feature_names': feature_names,
        'num_features': len(feature_names),
        'dataset_name': _lifestyle_meta.get('dataset_name'),
        'dataset_size': _lifestyle_meta.get('dataset_size'),
        'selected_threshold': _lifestyle_meta.get('selected_threshold'),
        'metrics': _lifestyle_meta.get('metrics') or _lifestyle_meta.get('test_metrics', {}),
        'status': 'loaded',
    }
    return jsonify(info), 200


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


# ── ANALYTICS PAGE ────────────────────────────
@app.route('/analytics')
def analytics():
    if 'user' not in session:
        flash('Please log in to view analytics.', 'error')
        return redirect('/login')
    return render_template('analytics.html')


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    logger.info("Starting Student Mental Health Analyzer on http://127.0.0.1:5000")
    debug_mode = os.environ.get('FLASK_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    app.run(debug=debug_mode, use_reloader=False, port=5000)
