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


def _load_quick_components():
    """Load quick-check-in model artifacts trained on the 5 daily inputs."""
    try:
        pre = joblib.load('models/quick_preprocessor.pkl')
        clf = joblib.load('models/quick_model.pkl')
        with open('models/quick_metadata.json', 'r', encoding='utf-8') as fh:
            meta = json.load(fh)
        with open('models/quick_features.json', 'r', encoding='utf-8') as fh:
            feat_meta = json.load(fh)
        meta = {**meta, **feat_meta}
        return pre, clf, meta
    except Exception as exc:
        logger.warning("Quick model artifacts unavailable: %s", exc)
        return None, None, None


def _load_severity_components():
    """Load multiclass severity model artifacts for shadow inference."""
    try:
        pre = joblib.load('models/severity_preprocessor.pkl')
        clf = joblib.load('models/severity_model.pkl')
        with open('models/severity_metadata.json', 'r', encoding='utf-8') as fh:
            meta = json.load(fh)
        with open('models/severity_features.json', 'r', encoding='utf-8') as fh:
            feat_meta = json.load(fh)
        meta = {**meta, **feat_meta}
        return pre, clf, meta
    except Exception as exc:
        logger.warning("Severity model artifacts unavailable: %s", exc)
        return None, None, None


# Loaded once at startup
_ml_model, _ml_scaler, _ml_feature_names = _load_ml_components()
if _ml_model is not None:
    logger.info("ML model loaded — final_model.pkl (binary v5.0)")
else:
    logger.info("Legacy binary model disabled — using severity/quick model pipeline")

# lifestyle model is no longer used in prediction flow (severity+quick only)
_lifestyle_pre, _lifestyle_model, _lifestyle_meta = None, None, None
logger.info("Lifestyle model inference path disabled — using severity/quick models")

_quick_pre, _quick_model, _quick_meta = _load_quick_components()
if _quick_model is not None:
    logger.info("Quick model loaded — quick_model.pkl")
else:
    logger.warning("Quick model unavailable — quick predictions disabled")

_severity_pre, _severity_model, _severity_meta = _load_severity_components()
if _severity_model is not None:
    logger.info("Severity model loaded — severity_model.pkl (shadow)")
else:
    logger.warning("Severity model unavailable — shadow severity predictions disabled")


# ─────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────




def _probability_to_category(probability: float, threshold: float = None) -> str:
    p = max(0.0, min(1.0, float(probability)))

    # Fallback to fixed bands if threshold is unavailable.
    if threshold is None:
        if p < 0.25:
            return "Excellent Mental Well-being"
        if p < 0.50:
            return "Moderate Stress Detected"
        if p < 0.75:
            return "High Stress & Anxiety"
        return "Severe Distress Detected"

    t = max(0.05, min(0.95, float(threshold)))
    low_band = max(0.0, min(1.0, 0.5 * t))
    high_band = max(t, min(1.0, 1.5 * t))

    if p < low_band:
        return "Excellent Mental Well-being"
    if p < t:
        return "Moderate Stress Detected"
    if p < high_band:
        return "High Stress & Anxiety"
    return "Severe Distress Detected"


def _probability_to_category_quick(probability: float, threshold: float) -> str:
    """Map quick-model probability to 4-level category with wider middle bands.

    Quick model thresholds are often low after calibration (for binary screening).
    Using full-mode bands can overproduce "Excellent". This mapping keeps
    categories responsive for daily check-ins.
    """
    p = max(0.0, min(1.0, float(probability)))
    t = max(0.05, min(0.95, float(threshold)))

    low_band = max(0.0, min(1.0, 0.25 * t))
    high_band = max(t, min(1.0, 2.0 * t))

    if p < low_band:
        return "Excellent Mental Well-being"
    if p < t:
        return "Moderate Stress Detected"
    if p < high_band:
        return "High Stress & Anxiety"
    return "Severe Distress Detected"


def _probability_to_score(probability: float) -> int:
    p = max(0.0, min(1.0, float(probability)))
    return int(round(p * 40.0))


def _probability_to_score_quick(probability: float, threshold: float) -> int:
    """Convert quick-model probability into a 0-40 score aligned with quick bands."""
    p = max(0.0, min(1.0, float(probability)))
    t = max(0.05, min(0.95, float(threshold)))
    low_band = max(0.0, min(1.0, 0.25 * t))
    high_band = max(t, min(1.0, 2.0 * t))

    eps = 1e-9
    if p < low_band:
        # Excellent: 0-9
        ratio = p / max(low_band, eps)
        return int(round(ratio * 9.0))
    if p < t:
        # Moderate: 10-19
        ratio = (p - low_band) / max(t - low_band, eps)
        return int(round(10.0 + ratio * 9.0))
    if p < high_band:
        # High: 20-29
        ratio = (p - t) / max(high_band - t, eps)
        return int(round(20.0 + ratio * 9.0))

    # Severe: 30-40
    ratio = (p - high_band) / max(1.0 - high_band, eps)
    ratio = max(0.0, min(1.0, ratio))
    return int(round(30.0 + ratio * 10.0))


def _to_float(value, default):
    try:
        if value is None or value == '':
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _map_binary_value(value, default=0.0):
    if value is None:
        return float(default)
    txt = str(value).strip().lower()
    if txt in {'1', 'yes', 'true'}:
        return 1.0
    if txt in {'0', 'no', 'false'}:
        return 0.0
    return _to_float(value, default)


def _map_counseling_value(value, default=0.0):
    if value is None:
        return float(default)
    txt = str(value).strip().lower()
    if txt == 'never':
        return 0.0
    if txt == 'occasionally':
        return 1.0
    if txt == 'frequently':
        return 2.0
    return _to_float(value, default)


def _mean_or_default(rows, key, default):
    vals = []
    for row in rows or []:
        try:
            val = row.get(key)
            if val is None:
                continue
            vals.append(float(val))
        except Exception:
            continue
    if not vals:
        return float(default)
    return float(np.mean(vals))


def _build_severity_shadow_payload(profile, student_id):
    """Build canonical severity payload using form, profile, and history fallbacks."""
    recent_full = []
    if student_id:
        try:
            recent_full = get_full_assessments(student_id, limit=10)
        except Exception:
            recent_full = []

    recent_mood = []
    if student_id:
        try:
            recent_mood = get_mood_history(student_id, days=7)
        except Exception:
            recent_mood = []

    mood_to_stress = {
        '😊': 1.5,
        '😐': 2.5,
        '😤': 3.5,
        '😰': 4.5,
        '😢': 4.0,
    }
    mood_stress_proxy = np.mean([mood_to_stress.get((m.get('mood') or '').strip(), 3.0) for m in recent_mood]) if recent_mood else 3.0

    sleep_default = _mean_or_default(recent_full, 'sleep_duration', 7.0)
    study_default = _mean_or_default(recent_full, 'study_hours', 3.0)
    social_default = _mean_or_default(recent_full, 'social_media', 2.0)
    activity_default = _mean_or_default(recent_full, 'physical_activity', 1.5)
    stress_default = _mean_or_default(recent_full, 'stress_level', mood_stress_proxy)
    anxiety_default = _mean_or_default(recent_full, 'anxiety', 3.0)
    support_default = _mean_or_default(recent_full, 'social_support', 3.0)

    payload = {
        'Age': _to_float(profile.get('age'), 21.0),
        'CGPA': _to_float(profile.get('cgpa'), 3.0),
        'Sleep_Duration': _to_float(request.form.get('Sleep_Duration'), sleep_default),
        'Study_Hours': _to_float(request.form.get('Study_Hours'), study_default),
        'Social_Media': _to_float(request.form.get('Social_Media'), social_default),
        'Physical_Activity': _to_float(request.form.get('Physical_Activity'), activity_default),
        'Stress_Level': _to_float(request.form.get('Stress_Level'), stress_default),
        'Anxiety_Score': _to_float(request.form.get('Anxiety_Score') or request.form.get('Anxiety_Level'), anxiety_default),
        'Social_Support': _to_float(request.form.get('Social_Support'), support_default),
        'Financial_Stress': _to_float(request.form.get('Financial_Stress'), 3.0),
        'Sleep_Quality': _to_float(request.form.get('Sleep_Quality'), 3.0),
        'Diet_Quality': _to_float(request.form.get('Diet_Quality'), 3.0),
        'Counseling_Service_Use': _map_counseling_value(request.form.get('Counseling_Service_Use'), 0.0),
        'Family_History': _map_binary_value(request.form.get('Family_History'), 0.0),
        'Gender': str(profile.get('gender') or request.form.get('Gender') or 'Other'),
        'Department': str(profile.get('department') or request.form.get('Department') or 'General'),
        'Residence_Type': str(request.form.get('Residence_Type') or 'Unknown'),
        'Relationship_Status': str(request.form.get('Relationship_Status') or 'Unknown'),
        'Substance_Use': str(request.form.get('Substance_Use') or 'Unknown'),
        'Chronic_Illness': str(request.form.get('Chronic_Illness') or 'Unknown'),
        'source_dataset': 'app_submission',
    }

    # Keep values inside training-time bounds.
    payload['Age'] = max(16.0, min(40.0, payload['Age']))
    payload['CGPA'] = max(0.0, min(10.0, payload['CGPA']))
    payload['Sleep_Duration'] = max(2.0, min(12.0, payload['Sleep_Duration']))
    payload['Study_Hours'] = max(0.0, min(12.0, payload['Study_Hours']))
    payload['Social_Media'] = max(0.0, min(12.0, payload['Social_Media']))
    payload['Physical_Activity'] = max(0.0, min(6.0, payload['Physical_Activity']))
    payload['Stress_Level'] = max(0.0, min(5.0, payload['Stress_Level']))
    payload['Anxiety_Score'] = max(0.0, min(5.0, payload['Anxiety_Score']))
    payload['Social_Support'] = max(0.0, min(5.0, payload['Social_Support']))
    payload['Financial_Stress'] = max(0.0, min(5.0, payload['Financial_Stress']))
    payload['Sleep_Quality'] = max(0.0, min(5.0, payload['Sleep_Quality']))
    payload['Diet_Quality'] = max(0.0, min(5.0, payload['Diet_Quality']))
    payload['Counseling_Service_Use'] = max(0.0, min(2.0, payload['Counseling_Service_Use']))
    payload['Family_History'] = max(0.0, min(1.0, payload['Family_History']))
    return payload


def _run_shadow_severity_prediction(profile, student_id, current_result, mode):
    if _severity_model is None or _severity_pre is None:
        return None

    try:
        features = []
        features.extend(_severity_meta.get('numeric_features', []))
        features.extend(_severity_meta.get('categorical_features', []))
        if not features:
            return None

        payload = _build_severity_shadow_payload(profile, student_id)
        row = {}
        for feature in features:
            if feature in ('Gender', 'Department', 'Residence_Type', 'Relationship_Status', 'Substance_Use', 'Chronic_Illness', 'source_dataset'):
                row[feature] = str(payload.get(feature, 'Unknown'))
            else:
                row[feature] = float(payload.get(feature, 0.0))

        X_shadow = pd.DataFrame([row], columns=features)
        X_shadow_t = _severity_pre.transform(X_shadow)
        pred_idx = int(_severity_model.predict(X_shadow_t)[0])
        proba = _severity_model.predict_proba(X_shadow_t)[0]
        pred_conf = float(np.max(proba))
        risk_prob = float(proba[2] + proba[3])

        idx_to_label = {
            0: 'Excellent Mental Well-being',
            1: 'Moderate Stress Detected',
            2: 'High Stress & Anxiety',
            3: 'Severe Distress Detected',
        }
        pred_label = idx_to_label.get(pred_idx, 'Moderate Stress Detected')
        logger.info(
            'Severity shadow | mode=%s user=%s current="%s" shadow="%s" conf=%.4f',
            mode,
            student_id,
            current_result,
            pred_label,
            pred_conf,
        )
        return {
            'severity_shadow_label': pred_label,
            'severity_shadow_confidence': pred_conf,
            'severity_shadow_risk_probability': risk_prob,
            'severity_shadow_class': pred_idx,
        }
    except Exception as exc:
        logger.warning('Severity shadow prediction failed: %s', exc)
        return None



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
        avg_30day_score=stats['avg_score_30days'],
        current_streak=stats.get('current_streak', 0)
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
    global _lifestyle_pre, _lifestyle_model, _lifestyle_meta, _quick_pre, _quick_model, _quick_meta, _severity_pre, _severity_model, _severity_meta

    if 'user' not in session:
        return redirect('/login')

    assessment_mode = (request.form.get('mode', 'quick') or 'quick').strip().lower()
    full_field_markers = [
        'Anxiety_Score',
        'Social_Support',
        'Financial_Stress',
        'Sleep_Quality',
        'Diet_Quality',
        'Counseling_Service_Use',
        'Family_History',
    ]
    if assessment_mode != 'full':
        if any((request.form.get(field) or '').strip() for field in full_field_markers):
            assessment_mode = 'full'

    if _quick_model is None:
        _quick_pre, _quick_model, _quick_meta = _load_quick_components()
    if _severity_model is None:
        _severity_pre, _severity_model, _severity_meta = _load_severity_components()

    severity_shadow_enabled = (os.environ.get('SEVERITY_SHADOW_MODE', '1').strip().lower() not in {'0', 'false', 'no'})

    if assessment_mode == 'full' and (_severity_model is None or _severity_pre is None):
        flash('Full assessment model is unavailable. Please contact admin or redeploy model artifacts.', 'error')
        return redirect('/test?mode=full')

    if assessment_mode == 'quick' and _quick_model is None:
        flash('Quick assessment model is unavailable. Please contact admin or redeploy model artifacts.', 'error')
        return redirect('/test?mode=quick')

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

    # Full assessment branch: primary output from severity model.
    if assessment_mode == 'full':
        # Build record directly from submitted form values.
        rec = {}
        for feat, val in request.form.items():
            if feat == 'mode':
                continue
            if val is None:
                rec[feat] = np.nan
                continue
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
        anxiety = _safe_float('Anxiety_Score', _safe_float('Anxiety_Level', 3))
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

        shadow_payload = _run_shadow_severity_prediction(
            profile=profile,
            student_id=session.get('user_id'),
            current_result='Moderate Stress Detected',
            mode='full',
        )
        if not shadow_payload:
            flash("Full assessment model is currently unavailable. Please try again shortly.", "error")
            return redirect('/test?mode=full')

        shadow_label_raw = str(shadow_payload.get('severity_shadow_label') or 'Moderate Stress Detected')
        prob = float(shadow_payload.get('severity_shadow_risk_probability', shadow_payload.get('severity_shadow_confidence', 0.5)))
        threshold = None
        total_score = _probability_to_score(prob)
        ml_category = _probability_to_category(prob, threshold=None)
        band = None
        if ml_category == "Excellent Mental Well-being":
            band = "Excellent"
        elif ml_category == "Moderate Stress Detected":
            band = "Moderate"
        elif ml_category == "High Stress & Anxiety":
            band = "High"
        else:
            band = "Severe"

        analysis = analyze_score_by_category(ml_category)
        logger.info(
            "Severity primary output | mode=%s | risk_prob=%.4f | final_label=%s | shadow_label=%s | final_score=%d",
            mode,
            prob,
            ml_category,
            shadow_label_raw,
            total_score,
        )
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

        display_score = total_score

        if extra_tips:
            analysis['tips'].extend(extra_tips)

        # Final canonicalization: keep full-mode label, score, and probability
        # derived from the same severity risk value right before rendering.
        try:
            if assessment_mode == 'full' and shadow_payload:
                final_prob = float(
                    shadow_payload.get(
                        'severity_shadow_risk_probability',
                        shadow_payload.get('severity_shadow_confidence', prob),
                    )
                )
                final_category = _probability_to_category(final_prob, threshold=None)
                analysis = analyze_score_by_category(final_category)
                total_score = _probability_to_score(final_prob)
                display_score = total_score
                prob = final_prob
                if final_category == "Excellent Mental Well-being":
                    band = "Excellent"
                elif final_category == "Moderate Stress Detected":
                    band = "Moderate"
                elif final_category == "High Stress & Anxiety":
                    band = "High"
                else:
                    band = "Severe"
        except Exception as exc:
            logger.warning("Final full-mode canonicalization failed: %s", exc)

        # Save as full assessment with ML features + canonical questionnaire fields.
        try:
            ml_features = {
                'stress_level': float(stress_val),
                'sleep_duration': float(sleep),
                'study_hours': float(study),
                'physical_activity': float(activity),
                'social_media': float(social_media_val) if social_media_val else 2.0
            }
            canonical_fields = {
                'sleep_quality': _to_float(request.form.get('Sleep_Quality'), 3.0),
                'diet_quality': _to_float(request.form.get('Diet_Quality'), 3.0),
                'financial_stress': _to_float(request.form.get('Financial_Stress'), 3.0),
                'counseling_service_use': str(request.form.get('Counseling_Service_Use') or 'Never'),
                'family_history': str(request.form.get('Family_History') or 'No'),
                'residence_type': str(request.form.get('Residence_Type') or 'Unknown'),
                'relationship_status': str(request.form.get('Relationship_Status') or 'Unknown'),
                'substance_use': str(request.form.get('Substance_Use') or 'Never'),
                'chronic_illness': str(request.form.get('Chronic_Illness') or 'Unknown'),
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
                ml_threshold=threshold,
                canonical_fields=canonical_fields,
                shadow_payload=shadow_payload,
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
                       display_probability=prob,
                       display_probability_label='Severity Risk Probability',
                       ml_threshold=threshold,
                       ml_band=band,
                       severity_shadow=shadow_payload,
                       assessment_mode=assessment_mode,
                       profile=profile)
        # if lifestyle model not loaded fall through to normal path

    # Quick mode: strict ML-only inference using the dedicated quick model.
    quick_features = _quick_meta.get(
        'quick_features',
        [
            'Sleep_Duration',
            'Study_Hours',
            'Social_Media',
            'Physical_Activity',
            'Stress_Level',
            'Age',
            'CGPA',
            'Gender',
            'Department',
            'sleep_study_ratio',
            'stress_x_sleep',
            'study_x_stress',
            'activity_social_balance',
        ],
    )
    quick_defaults = {
        'Sleep_Duration': 7.0,
        'Study_Hours': 3.0,
        'Social_Media': 2.0,
        'Physical_Activity': 1.5,
        'Stress_Level': 3.0,
        'Age': 21.0,
        'CGPA': 3.0,
    }
    profile_feature_map = {
        'Age': profile.get('age'),
        'CGPA': profile.get('cgpa'),
        'Gender': profile.get('gender'),
        'Department': profile.get('department'),
    }

    try:
        base_row = {}
        for feature in ['Sleep_Duration', 'Study_Hours', 'Social_Media', 'Physical_Activity', 'Stress_Level', 'Age', 'CGPA']:
            raw = request.form.get(feature)
            if raw is None and profile_feature_map.get(feature) is not None:
                raw = profile_feature_map.get(feature)
            if raw is None:
                raw = quick_defaults.get(feature, 0.0)
            base_row[feature] = float(raw)

        base_row['Gender'] = str(profile_feature_map.get('Gender') or request.form.get('Gender') or 'Unknown')
        base_row['Department'] = str(profile_feature_map.get('Department') or request.form.get('Department') or 'General')

        base_row['sleep_study_ratio'] = base_row['Sleep_Duration'] / (base_row['Study_Hours'] + 1.0)
        base_row['stress_x_sleep'] = base_row['Stress_Level'] * base_row['Sleep_Duration']
        base_row['study_x_stress'] = base_row['Study_Hours'] * base_row['Stress_Level']
        base_row['activity_social_balance'] = base_row['Physical_Activity'] - 0.5 * base_row['Social_Media']

        quick_row = {}
        for feature in quick_features:
            if feature in ('Gender', 'Department'):
                quick_row[feature] = str(base_row.get(feature, 'Unknown'))
            else:
                quick_row[feature] = float(base_row.get(feature, quick_defaults.get(feature, 0.0)))

        quick_df = pd.DataFrame([quick_row], columns=quick_features)
        quick_X = _quick_pre.transform(quick_df)
        proba = _quick_model.predict_proba(quick_X)[0]
        classes = getattr(_quick_model, 'classes_', None)
        if classes is None:
            classes = np.arange(len(proba))

        class_prob = {}
        for idx, cls in enumerate(classes):
            class_prob[int(cls)] = float(proba[idx])

        idx_to_label = {
            0: 'Excellent Mental Well-being',
            1: 'Moderate Stress Detected',
            2: 'High Stress & Anxiety',
            3: 'Severe Distress Detected',
        }

        if len(class_prob) >= 4:
            pred_idx = max(class_prob, key=class_prob.get)
            ml_category = idx_to_label.get(pred_idx, 'Moderate Stress Detected')
            ml_prob = float(class_prob.get(2, 0.0) + class_prob.get(3, 0.0))
            ml_threshold = None
            total_score = _probability_to_score(ml_prob)
            display_probability_label = 'Severity Risk Probability'
        else:
            # Backward compatibility if an older binary quick model is still loaded.
            ml_prob = float(class_prob.get(1, 0.0))
            ml_threshold = float(_quick_meta.get('selected_threshold', 0.5))
            ml_category = _probability_to_category_quick(ml_prob, ml_threshold)
            total_score = _probability_to_score_quick(ml_prob, ml_threshold)
            display_probability_label = 'Model Probability'
    except Exception as exc:
        logger.error("Quick model prediction failed: %s", exc)
        flash("Quick assessment model failed to run. Please try again.", "error")
        return redirect('/test?mode=quick')

    analysis = analyze_score_by_category(ml_category)

    stress_value = _clamp_1_5(request.form.get('Stress_Level', 3), 3)
    sleep_hours = float(request.form.get('Sleep_Duration', 7.0))
    study_hours = float(request.form.get('Study_Hours', 3.0))
    social_media_hours = float(request.form.get('Social_Media', 2.0))
    activity_hours = float(request.form.get('Physical_Activity', 1.5))

    breakdown = [
        {"label": "Sleep (hrs)", "value": sleep_hours, "pct": min((sleep_hours / 9.0) * 100, 100), "color": "#6c63ff, #a29bfe"},
        {"label": "Study (hrs)", "value": study_hours, "pct": min((study_hours / 8.0) * 100, 100), "color": "#fd79a8, #e84393"},
        {"label": "Social media (hrs)", "value": social_media_hours, "pct": min((social_media_hours / 6.0) * 100, 100), "color": "#00cec9, #00b894"},
        {"label": "Physical activity (hrs)", "value": activity_hours, "pct": min((activity_hours / 3.5) * 100, 100), "color": "#55efc4, #00b894"},
        {"label": "Stress Level", "value": stress_value, "pct": stress_value * 20, "color": "#e17055, #d63031"},
    ]

    try:
        stored_quick_scores = {
            'stress': stress_value,
            'anxiety': 3,
            'sleep_quality': _sleep_hours_to_quality(sleep_hours),
            'focus': 3,
            'social': 3,
            'sadness': 3,
            'energy': 3,
            'overwhelm': 3,
        }
        create_quick_assessment(
            student_id=session.get('user_id'),
            scores=stored_quick_scores,
            total_score=total_score,
            result_category=analysis['result']
        )
    except Exception as e:
        logger.error(f"Quick assessment save failed: {e}")

    shadow_payload = None

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
        ml_probability=ml_prob,
        display_probability=ml_prob,
        display_probability_label=display_probability_label,
        ml_threshold=ml_threshold,
        severity_shadow=shadow_payload,
        assessment_mode=assessment_mode,
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
                'severity_shadow_label': test.get('severity_shadow_label'),
                'severity_shadow_confidence': test.get('severity_shadow_confidence'),
                'severity_shadow_class': test.get('severity_shadow_class'),
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
    if _severity_model is None or _severity_meta is None:
        return jsonify({'error': 'Model not loaded'}), 503

    numeric_features = _severity_meta.get('numeric_features', [])
    categorical_features = _severity_meta.get('categorical_features', [])
    feature_names = numeric_features + categorical_features

    info = {
        'model_type': _severity_meta.get('model_type', 'Unknown'),
        'model_name': _severity_meta.get('model_name', 'severity_model.pkl'),
        'version': _severity_meta.get('version', 'severity-current'),
        'target': _severity_meta.get('target', 'Severity_Level'),
        'feature_names': feature_names,
        'num_features': len(feature_names),
        'dataset_name': _severity_meta.get('dataset_name') or _severity_meta.get('dataset'),
        'dataset_size': _severity_meta.get('dataset_size'),
        'selected_threshold': _severity_meta.get('selected_threshold'),
        'metrics': _severity_meta.get('metrics') or _severity_meta.get('test_metrics', {}),
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
