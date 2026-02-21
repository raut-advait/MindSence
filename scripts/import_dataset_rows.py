"""Import rows from the Kaggle CSV into a DB table `imported_test_results`.

This creates a stub student per row (since the CSV lacks names/emails) and
stores features discovered in `scripts/preprocess_and_train.py`.
"""
import argparse
import sqlite3
import os
import pandas as pd
from datetime import datetime


def map_yes_no(val):
    if pd.isna(val):
        return 0
    s = str(val).strip().lower()
    if s in ('yes','y','true','1'):
        return 1
    if s in ('no','n','false','0'):
        return 0
    if 'yes' in s:
        return 1
    if 'no' in s:
        return 0
    return 0


def map_gender(val):
    if pd.isna(val):
        return 0
    s = str(val).strip().lower()
    if 'female' in s:
        return 1
    if 'male' in s:
        return 0
    return 2


def main(csv_path, db_path):
    if not os.path.exists(csv_path):
        raise SystemExit(f"CSV not found: {csv_path}")
    if not os.path.exists(db_path):
        raise SystemExit(f"DB not found: {db_path}. Run your app or `python init_db.py` to create it.")

    df = pd.read_csv(csv_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Create imported_test_results table if missing
    cur.execute('''
        CREATE TABLE IF NOT EXISTS imported_test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            name TEXT,
            email TEXT,
            age REAL,
            gender INTEGER,
            cgpa REAL,
            year INTEGER,
            course TEXT,
            depression INTEGER,
            anxiety INTEGER,
            panic INTEGER,
            sought_treatment INTEGER,
            total_score REAL,
            result TEXT,
            predicted_prob REAL,
            predicted_category TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    for _, r in df.iterrows():
        name = r.get('Name') or r.get('name') or 'imported'
        email = r.get('Email') or r.get('email') or None
        age = pd.to_numeric(r.get('Age'), errors='coerce') if 'Age' in r.index else None
        gender = map_gender(r.get('Choose your gender')) if 'Choose your gender' in r.index else 0
        cgpa = pd.to_numeric(str(r.get('What is your CGPA?')).replace('%',''), errors='coerce') if 'What is your CGPA?' in r.index else None
        year = None
        if 'Your current year of Study' in r.index:
            try:
                year = int(str(r.get('Your current year of Study')).strip().split()[0])
            except Exception:
                year = None
        course = r.get('What is your course?') if 'What is your course?' in r.index else None
        depression = map_yes_no(r.get('Do you have Depression?')) if 'Do you have Depression?' in r.index else 0
        anxiety = map_yes_no(r.get('Do you have Anxiety?')) if 'Do you have Anxiety?' in r.index else 0
        panic = map_yes_no(r.get('Do you have Panic attack?')) if 'Do you have Panic attack?' in r.index else 0
        sought = map_yes_no(r.get('Did you seek any specialist for a treatment?')) if 'Did you seek any specialist for a treatment?' in r.index else 0

        # compute a simple total_score as sum of available numeric features
        total_score = 0
        for v in (age, cgpa, year, depression, anxiety, panic, sought):
            try:
                total_score += float(v) if v is not None else 0
            except Exception:
                pass

        # create stub student
        if email:
            cur.execute("INSERT OR IGNORE INTO students (name,email,password,dob) VALUES (?,?,?,?)",
                        (name, email, 'imported', None))
            cur.execute("SELECT id FROM students WHERE email=?", (email,))
            row = cur.fetchone()
            sid = row[0] if row else None
        else:
            import uuid
            gen_email = f"imported+{uuid.uuid4().hex}@example.invalid"
            cur.execute("INSERT OR IGNORE INTO students (name,email,password,dob) VALUES (?,?,?,?)",
                        (name, gen_email, 'imported', None))
            cur.execute("SELECT id FROM students WHERE email=?", (gen_email,))
            row2 = cur.fetchone()
            sid = row2[0] if row2 else None

        cur.execute(
            '''INSERT INTO imported_test_results
               (student_id,name,email,age,gender,cgpa,year,course,depression,anxiety,panic,sought_treatment,total_score,result,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (sid, name, email, float(age) if age is not None else None, int(gender) if gender is not None else None,
             float(cgpa) if cgpa is not None else None, int(year) if year is not None else None, course,
             int(depression), int(anxiety), int(panic), int(sought), float(total_score), None, datetime.now().isoformat())
        )

    conn.commit()
    conn.close()
    print('Imported rows into imported_test_results')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--db', default='database.db')
    args = p.parse_args()
    main(args.csv, args.db)
