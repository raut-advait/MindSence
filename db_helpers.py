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
) -> Optional[int]:
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor) if _is_postgres_conn(conn) else conn.cursor()
    try:
        assessment_id = _insert_and_get_id(
            conn,
            cur,
            """
            INSERT INTO full_assessments
            (student_id, stress_level, sleep_duration, study_hours, physical_activity, social_media,
             anxiety, focus, social_support, sadness, energy, overwhelm, total_score, result_category,
             ml_probability, ml_threshold, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            "amazing": "😊",
            "good": "😊",
            "okay": "😐",
            "stressed": "😰",
            "anxious": "😰",
            "sad": "😢",
        }
        emoji_to_label = {
            "😊": "Good",
            "😐": "Okay",
            "😰": "Stressed",
            "😢": "Sad",
            "😤": "Stressed",
        }
        allowed_emojis = {"😊", "😐", "😰", "😢", "😤"}

        normalized_mood = (mood or "").strip()
        normalized_mood = mood_label_to_emoji.get(normalized_mood.lower(), normalized_mood)
        if normalized_mood not in allowed_emojis:
            return False, "Invalid mood value"

        _execute(
            cur,
            """
            SELECT id, mood FROM mood_logs
            WHERE student_id = ? AND date(created_at) = date('now')
            LIMIT 1
            """,
            (student_id,),
        )
        existing = _row_to_dict(cur.fetchone())
        if existing:
            existing_label = emoji_to_label.get(existing["mood"], "today")
            return False, f"You already logged your mood today ({existing_label}). Try again tomorrow!"

        _execute(
            cur,
            """
            INSERT INTO mood_logs (student_id, mood, note, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, normalized_mood, note, get_ist_timestamp()),
        )
        conn.commit()
        saved_label = (mood or "").strip().title() or emoji_to_label.get(normalized_mood, "Mood")
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
        return _rows_to_dicts(cur.fetchall())
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

        return {
            "quick_assessments": int(quick_count),
            "full_assessments": int(full_count),
            "latest_quick": latest_quick,
            "latest_full": latest_full,
            "avg_score_30days": avg_30day.get("avg_score") if avg_30day else None,
            "mood_distribution": mood_dist,
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
