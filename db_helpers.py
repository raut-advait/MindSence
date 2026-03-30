"""
Database helper functions for mental health analyzer.
PostgreSQL-only via DATABASE_URL.
"""

import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("mental_health_app")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    RealDictCursor = None

IST = timezone(timedelta(hours=5, minutes=30))


def get_ist_timestamp() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _database_url() -> Optional[str]:
    return os.environ.get("DATABASE_URL")


def _is_postgres_url(url: Optional[str]) -> bool:
    if not url:
        return False
    return url.startswith("postgres://") or url.startswith("postgresql://")


def _normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


def _is_postgres_conn(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")


def _adapt_query_for_postgres(query: str) -> str:
    q = query.replace("?", "%s")
    q = q.replace("date('now')", "CURRENT_DATE")
    q = re.sub(
        r"date\('now',\s*'-([0-9]+) days'\)",
        r"(CURRENT_DATE - INTERVAL '\1 days')",
        q,
    )
    return q


def _execute(cur, query: str, params: Tuple = ()):
    if cur.__class__.__module__.startswith("psycopg2"):
        cur.execute(_adapt_query_for_postgres(query), params)
    else:
        cur.execute(query, params)


def _row_to_dict(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return dict(row)
    try:
        return dict(row)
    except Exception:
        return None


def _rows_to_dicts(rows):
    result = []
    for row in rows:
        as_dict = _row_to_dict(row)
        if as_dict is not None:
            result.append(as_dict)
    return result


def _scalar(row):
    if row is None:
        return None
    if isinstance(row, dict):
        return next(iter(row.values())) if row else None
    return row[0]


def _parse_mood_label_from_note(note: Optional[str]) -> Optional[str]:
    if not note:
        return None
    match = re.search(r"(?:^|\n)__mood_label__:(Amazing|Good|Okay|Stressed|Anxious|Sad)(?:\n|$)", str(note), re.IGNORECASE)
    if not match:
        return None
    return match.group(1).title()


def _resolve_mood_label(mood_value: Optional[str], note: Optional[str] = None) -> str:
    label_from_note = _parse_mood_label_from_note(note)
    if label_from_note:
        return label_from_note

    fallback = {
        "😊": "Good",
        "😐": "Okay",
        "😰": "Stressed",
        "😢": "Sad",
        "😤": "Amazing",
    }
    return fallback.get((mood_value or "").strip(), "Mood")


def _compose_mood_note(label: str, note: Optional[str]) -> str:
    clean_note = (note or "").strip()
    marker = f"__mood_label__:{label}"
    if not clean_note:
        return marker
    return f"{marker}\n{clean_note}"


def get_db_connection():
    database_url = _database_url()

    if not _is_postgres_url(database_url):
        raise RuntimeError("DATABASE_URL must be a valid PostgreSQL URL (postgresql://...).")
    if psycopg2 is None or RealDictCursor is None:
        raise RuntimeError("Postgres selected but psycopg2 is not installed.")

    conn = psycopg2.connect(_normalize_postgres_url(database_url))
    return conn


def init_db() -> bool:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        _execute(
            cur,
            """
            CREATE TABLE IF NOT EXISTS students (
                id                BIGSERIAL PRIMARY KEY,
                name              TEXT NOT NULL,
                email             TEXT NOT NULL UNIQUE,
                password          TEXT NOT NULL,
                dob               TEXT,
                age               INTEGER,
                gender            TEXT,
                department        TEXT,
                academic_year     TEXT,
                cgpa              DOUBLE PRECISION,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        _execute(
            cur,
            """
            CREATE TABLE IF NOT EXISTS quick_assessments (
                id                BIGSERIAL PRIMARY KEY,
                student_id        BIGINT NOT NULL,
                stress            INTEGER CHECK(stress BETWEEN 1 AND 5),
                anxiety           INTEGER CHECK(anxiety BETWEEN 1 AND 5),
                sleep_quality     INTEGER CHECK(sleep_quality BETWEEN 1 AND 5),
                focus             INTEGER CHECK(focus BETWEEN 1 AND 5),
                social            INTEGER CHECK(social BETWEEN 1 AND 5),
                sadness           INTEGER CHECK(sadness BETWEEN 1 AND 5),
                energy            INTEGER CHECK(energy BETWEEN 1 AND 5),
                overwhelm         INTEGER CHECK(overwhelm BETWEEN 1 AND 5),
                total_score       INTEGER CHECK(total_score BETWEEN 0 AND 40),
                result_category   TEXT,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """,
        )
        _execute(cur, "CREATE INDEX IF NOT EXISTS idx_quick_student_date ON quick_assessments(student_id, created_at)")

        _execute(
            cur,
            """
            CREATE TABLE IF NOT EXISTS full_assessments (
                id                BIGSERIAL PRIMARY KEY,
                student_id        BIGINT NOT NULL,
                stress_level      DOUBLE PRECISION,
                sleep_duration    DOUBLE PRECISION,
                study_hours       DOUBLE PRECISION,
                physical_activity DOUBLE PRECISION,
                social_media      DOUBLE PRECISION,
                anxiety           INTEGER CHECK(anxiety BETWEEN 1 AND 5),
                focus             INTEGER CHECK(focus BETWEEN 1 AND 5),
                social_support    INTEGER CHECK(social_support BETWEEN 1 AND 5),
                sadness           INTEGER CHECK(sadness BETWEEN 1 AND 5),
                energy            INTEGER CHECK(energy BETWEEN 1 AND 5),
                overwhelm         INTEGER CHECK(overwhelm BETWEEN 1 AND 5),
                total_score       INTEGER CHECK(total_score BETWEEN 0 AND 40),
                result_category   TEXT,
                ml_probability    DOUBLE PRECISION,
                ml_threshold      DOUBLE PRECISION,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """,
        )
        _execute(cur, "CREATE INDEX IF NOT EXISTS idx_full_student_date ON full_assessments(student_id, created_at)")

        # Additive migration for dataset-aligned full-assessment fields and shadow outputs.
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS sleep_quality DOUBLE PRECISION")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS diet_quality DOUBLE PRECISION")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS financial_stress DOUBLE PRECISION")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS counseling_service_use TEXT")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS family_history TEXT")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS residence_type TEXT")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS relationship_status TEXT")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS substance_use TEXT")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS chronic_illness TEXT")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS severity_shadow_label TEXT")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS severity_shadow_confidence DOUBLE PRECISION")
        _execute(cur, "ALTER TABLE full_assessments ADD COLUMN IF NOT EXISTS severity_shadow_class INTEGER")

        _execute(
            cur,
            """
            CREATE TABLE IF NOT EXISTS mood_logs (
                id                BIGSERIAL PRIMARY KEY,
                student_id        BIGINT NOT NULL,
                mood              TEXT NOT NULL CHECK(mood IN ('😊', '😐', '😢', '😰', '😤')),
                note              TEXT,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
            """,
        )
        _execute(cur, "CREATE INDEX IF NOT EXISTS idx_mood_student_date ON mood_logs(student_id, created_at)")

        conn.commit()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    finally:
        conn.close()


def _insert_and_get_id(conn, cur, query: str, params: Tuple):
    _execute(cur, f"{query} RETURNING id", params)
    return _scalar(cur.fetchone())


def create_student(name: str, email: str, password: str, **profile_data) -> Optional[int]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        student_id = _insert_and_get_id(
            conn,
            cur,
            """
            INSERT INTO students (name, email, password, dob, age, gender, department, academic_year, cgpa)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                email.lower(),
                password,
                profile_data.get("dob"),
                profile_data.get("age"),
                profile_data.get("gender"),
                profile_data.get("department"),
                profile_data.get("academic_year"),
                profile_data.get("cgpa"),
            ),
        )
        conn.commit()
        return student_id
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return None
        logger.error(f"Error creating student: {e}")
        return None
    finally:
        conn.close()


def get_student(student_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(cur, "SELECT * FROM students WHERE id = ?", (student_id,))
        return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_student_by_email(email: str) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(cur, "SELECT * FROM students WHERE email = ?", (email.lower(),))
        return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def update_student(student_id: int, **updates) -> bool:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        allowed_fields = ["name", "age", "gender", "department", "academic_year", "cgpa", "dob"]
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        if not updates:
            return True

        updates["updated_at"] = get_ist_timestamp()
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = tuple(list(updates.values()) + [student_id])
        _execute(cur, f"UPDATE students SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating student {student_id}: {e}")
        return False
    finally:
        conn.close()


def create_quick_assessment(student_id: int, scores: Dict, total_score: int, result_category: str) -> Optional[int]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        assessment_id = _insert_and_get_id(
            conn,
            cur,
            """
            INSERT INTO quick_assessments
            (student_id, stress, anxiety, sleep_quality, focus, social, sadness, energy, overwhelm, total_score, result_category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                scores.get("stress", 3),
                scores.get("anxiety", 3),
                scores.get("sleep_quality", 3),
                scores.get("focus", 3),
                scores.get("social", 3),
                scores.get("sadness", 3),
                scores.get("energy", 3),
                scores.get("overwhelm", 3),
                total_score,
                result_category,
                get_ist_timestamp(),
            ),
        )
        conn.commit()
        return assessment_id
    except Exception as e:
        logger.error(f"Error creating quick assessment: {e}")
        return None
    finally:
        conn.close()


def get_quick_assessment(assessment_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(cur, "SELECT * FROM quick_assessments WHERE id = ?", (assessment_id,))
        return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_quick_assessments(student_id: int, limit: int = 30) -> List[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(
            cur,
            """
            SELECT * FROM quick_assessments
            WHERE student_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (student_id, limit),
        )
        return _rows_to_dicts(cur.fetchall())
    finally:
        conn.close()


def get_latest_quick_assessment(student_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(
            cur,
            """
            SELECT * FROM quick_assessments
            WHERE student_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (student_id,),
        )
        return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def create_full_assessment(
    student_id: int,
    ml_features: Dict,
    scores: Dict,
    total_score: int,
    result_category: str,
    ml_probability: Optional[float] = None,
    ml_threshold: Optional[float] = None,
    canonical_fields: Optional[Dict] = None,
    shadow_payload: Optional[Dict] = None,
) -> Optional[int]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        canonical_fields = canonical_fields or {}
        shadow_payload = shadow_payload or {}
        assessment_id = _insert_and_get_id(
            conn,
            cur,
            """
            INSERT INTO full_assessments
            (student_id, stress_level, sleep_duration, study_hours, physical_activity, social_media,
             anxiety, focus, social_support, sadness, energy, overwhelm, total_score, result_category,
             ml_probability, ml_threshold, sleep_quality, diet_quality, financial_stress,
             counseling_service_use, family_history, residence_type, relationship_status,
             substance_use, chronic_illness, severity_shadow_label, severity_shadow_confidence,
             severity_shadow_class, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                ml_features.get("stress_level", 3.0),
                ml_features.get("sleep_duration", 7.0),
                ml_features.get("study_hours", 3.0),
                ml_features.get("physical_activity", 1.5),
                ml_features.get("social_media", 2.0),
                scores.get("anxiety", 3),
                scores.get("focus", 3),
                scores.get("social_support", 3),
                scores.get("sadness", 3),
                scores.get("energy", 3),
                scores.get("overwhelm", 3),
                total_score,
                result_category,
                ml_probability,
                ml_threshold,
                canonical_fields.get("sleep_quality"),
                canonical_fields.get("diet_quality"),
                canonical_fields.get("financial_stress"),
                canonical_fields.get("counseling_service_use"),
                canonical_fields.get("family_history"),
                canonical_fields.get("residence_type"),
                canonical_fields.get("relationship_status"),
                canonical_fields.get("substance_use"),
                canonical_fields.get("chronic_illness"),
                shadow_payload.get("severity_shadow_label"),
                shadow_payload.get("severity_shadow_confidence"),
                shadow_payload.get("severity_shadow_class"),
                get_ist_timestamp(),
            ),
        )
        conn.commit()
        return assessment_id
    except Exception as e:
        logger.error(f"Error creating full assessment: {e}")
        return None
    finally:
        conn.close()


def get_full_assessment(assessment_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(cur, "SELECT * FROM full_assessments WHERE id = ?", (assessment_id,))
        return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_full_assessments(student_id: int, limit: int = 30) -> List[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(
            cur,
            """
            SELECT * FROM full_assessments
            WHERE student_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (student_id, limit),
        )
        return _rows_to_dicts(cur.fetchall())
    finally:
        conn.close()


def get_latest_full_assessment(student_id: int) -> Optional[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(
            cur,
            """
            SELECT * FROM full_assessments
            WHERE student_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (student_id,),
        )
        return _row_to_dict(cur.fetchone())
    finally:
        conn.close()


def get_all_assessments_by_type(student_id: int, assessment_type: str = "quick", limit: int = 30) -> List[Dict]:
    if assessment_type == "quick":
        return get_quick_assessments(student_id, limit)
    if assessment_type == "full":
        return get_full_assessments(student_id, limit)
    return []


def record_mood(student_id: int, mood: str, note: Optional[str] = None) -> Tuple[bool, str]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        mood_label_to_emoji = {
            "amazing": "😤",
            "good": "😊",
            "okay": "😐",
            "stressed": "😰",
            "anxious": "😰",
            "sad": "😢",
        }
        allowed_emojis = {"😊", "😐", "😰", "😢", "😤"}

        raw_mood = (mood or "").strip()
        lower_mood = raw_mood.lower()

        if lower_mood in mood_label_to_emoji:
            normalized_mood = mood_label_to_emoji[lower_mood]
            saved_label = raw_mood.title()
        else:
            normalized_mood = raw_mood
            saved_label = _resolve_mood_label(normalized_mood)

        if normalized_mood not in allowed_emojis:
            return False, "Invalid mood value"

        stored_note = _compose_mood_note(saved_label, note)

        _execute(
            cur,
            """
            SELECT id, mood, note FROM mood_logs
            WHERE student_id = ? AND date(created_at) = date('now')
            LIMIT 1
            """,
            (student_id,),
        )
        existing = _row_to_dict(cur.fetchone())
        if existing:
            existing_label = _resolve_mood_label(existing.get("mood"), existing.get("note"))
            return False, f"You already logged your mood today ({existing_label}). Try again tomorrow!"

        _execute(
            cur,
            """
            INSERT INTO mood_logs (student_id, mood, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, normalized_mood, stored_note, get_ist_timestamp()),
        )
        conn.commit()
        return True, f"Mood logged successfully! Your check-in: {saved_label}"
    except Exception as e:
        logger.error(f"Error recording mood: {e}")
        return False, f"Error recording mood: {str(e)}"
    finally:
        conn.close()


def get_mood_history(student_id: int, days: int = 7) -> List[Dict]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(
            cur,
            f"""
            SELECT id, mood, note, created_at FROM mood_logs
            WHERE student_id = ? AND date(created_at) >= date('now', '-{int(days)} days')
            ORDER BY created_at DESC
            """,
            (student_id,),
        )
        rows = _rows_to_dicts(cur.fetchall())
        for row in rows:
            row["mood_label"] = _resolve_mood_label(row.get("mood"), row.get("note"))
        return rows
    finally:
        conn.close()


def get_mood_stats(student_id: int, days: int = 7) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(
            cur,
            f"""
            SELECT mood, COUNT(*) as count FROM mood_logs
            WHERE student_id = ? AND date(created_at) >= date('now', '-{int(days)} days')
            GROUP BY mood
            """,
            (student_id,),
        )
        mood_dist = {row["mood"]: row["count"] for row in _rows_to_dicts(cur.fetchall())}

        _execute(
            cur,
            """
            SELECT mood FROM mood_logs
            WHERE student_id = ? AND date(created_at) = date('now')
            LIMIT 1
            """,
            (student_id,),
        )
        today_mood = _row_to_dict(cur.fetchone())

        return {
            "mood_distribution": mood_dist,
            "today_mood": today_mood["mood"] if today_mood else None,
            "latest_mood": today_mood["mood"] if today_mood else None,
            "total_logs": sum(mood_dist.values()),
            "total_logs_this_week": sum(mood_dist.values()),
        }
    finally:
        conn.close()


def get_student_dashboard_stats(student_id: int) -> Dict:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(cur, "SELECT COUNT(*) FROM quick_assessments WHERE student_id = ?", (student_id,))
        quick_count = _scalar(cur.fetchone()) or 0

        _execute(cur, "SELECT COUNT(*) FROM full_assessments WHERE student_id = ?", (student_id,))
        full_count = _scalar(cur.fetchone()) or 0

        _execute(
            cur,
            """
            SELECT total_score, result_category, created_at FROM quick_assessments
            WHERE student_id = ? ORDER BY created_at DESC LIMIT 1
            """,
            (student_id,),
        )
        latest_quick = _row_to_dict(cur.fetchone())

        _execute(
            cur,
            """
            SELECT total_score, result_category, ml_probability, created_at FROM full_assessments
            WHERE student_id = ? ORDER BY created_at DESC LIMIT 1
            """,
            (student_id,),
        )
        latest_full = _row_to_dict(cur.fetchone())

        _execute(
            cur,
            """
            SELECT AVG(total_score) as avg_score FROM quick_assessments
            WHERE student_id = ? AND date(created_at) >= date('now', '-30 days')
            """,
            (student_id,),
        )
        avg_30day = _row_to_dict(cur.fetchone())

        _execute(
            cur,
            """
            SELECT mood, COUNT(*) as count FROM mood_logs
            WHERE student_id = ? AND date(created_at) >= date('now', '-7 days')
            GROUP BY mood
            """,
            (student_id,),
        )
        mood_dist = {row["mood"]: row["count"] for row in _rows_to_dicts(cur.fetchall())}

        _execute(
            cur,
            """
            SELECT DISTINCT date(created_at) AS log_date
            FROM mood_logs
            WHERE student_id = ?
            ORDER BY log_date DESC
            """,
            (student_id,),
        )
        date_rows = _rows_to_dicts(cur.fetchall())

        logged_dates = set()
        for row in date_rows:
            raw = row.get("log_date")
            if raw is None:
                continue
            if hasattr(raw, "year") and hasattr(raw, "month") and hasattr(raw, "day"):
                logged_dates.add(raw)
                continue
            try:
                logged_dates.add(datetime.fromisoformat(str(raw)).date())
            except Exception:
                continue

        today = datetime.now(IST).date()
        start = None
        if today in logged_dates:
            start = today
        elif (today - timedelta(days=1)) in logged_dates:
            start = today - timedelta(days=1)

        current_streak = 0
        cursor_day = start
        while cursor_day is not None and cursor_day in logged_dates:
            current_streak += 1
            cursor_day = cursor_day - timedelta(days=1)

        return {
            "quick_assessments": int(quick_count),
            "full_assessments": int(full_count),
            "latest_quick": latest_quick,
            "latest_full": latest_full,
            "avg_score_30days": avg_30day.get("avg_score") if avg_30day else None,
            "mood_distribution": mood_dist,
            "current_streak": int(current_streak),
        }
    finally:
        conn.close()


def get_all_students_aggregate_stats() -> Dict:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        _execute(cur, "SELECT COUNT(*) FROM students")
        total_students = _scalar(cur.fetchone()) or 0

        _execute(cur, "SELECT COUNT(*) FROM quick_assessments")
        total_quick = _scalar(cur.fetchone()) or 0

        _execute(cur, "SELECT COUNT(*) FROM full_assessments")
        total_full = _scalar(cur.fetchone()) or 0

        _execute(cur, "SELECT COUNT(DISTINCT student_id) FROM mood_logs")
        students_with_moods = _scalar(cur.fetchone()) or 0

        _execute(
            cur,
            """
            SELECT result_category, COUNT(*) as count FROM quick_assessments
            GROUP BY result_category
            """,
        )
        category_dist = {row["result_category"]: row["count"] for row in _rows_to_dicts(cur.fetchall())}

        return {
            "total_students": int(total_students),
            "total_quick_assessments": int(total_quick),
            "total_full_assessments": int(total_full),
            "students_with_mood_logs": int(students_with_moods),
            "category_distribution": category_dist,
        }
    finally:
        conn.close()
