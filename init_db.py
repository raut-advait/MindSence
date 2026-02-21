"""
Run this script once to reset the database.
The app also auto-initialises the DB on startup via init_db().
"""
import sqlite3
import os

# Remove old DB if you want a clean slate
if os.path.exists("database.db"):
    os.remove("database.db")
    print("Old database removed.")

conn = sqlite3.connect("database.db")
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

conn.commit()
conn.close()
print("Database initialised successfully!")
