"""Import cleaned CSV rows into database.db's students and test_results tables.

Expected columns (preferred):
- name, email, dob, stress, anxiety, sleep, focus, social, sadness, energy, overwhelm, total_score, result

If some columns are missing the script will try to map numeric columns to the test fields.

Usage:
    python scripts/import_to_db.py --csv data/StudentMentalHealth_cleaned.csv
"""
import argparse
import sqlite3
import os
import pandas as pd


def main(csv_path, db_path):
    if not os.path.exists(csv_path):
        raise SystemExit(f"CSV not found: {csv_path}")
    if not os.path.exists(db_path):
        raise SystemExit(f"DB not found: {db_path}. Run your app or `python init_db.py` to create it.")

    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Determine columns
    expected = ['stress','anxiety','sleep','focus','social','sadness','energy','overwhelm']

    # If expected columns not present, try to use first 8 numeric
    if not all(c in df.columns for c in expected):
        numeric = df.select_dtypes(include=['int64','float64']).columns.tolist()
        if len(numeric) >= 8:
            mapping = numeric[:8]
            df2 = df.copy()
            df2.columns = list(df.columns)
            df_used = df2
            print("Using numeric columns for test fields:", mapping)
            df_used = df2
            # rename the first 8 numeric columns to expected names
            rename_map = {numeric[i]: expected[i] for i in range(min(8, len(numeric)))}
            df_used = df2.rename(columns=rename_map)
        else:
            raise SystemExit("CSV doesn't contain enough numeric columns to map to test fields.")
    else:
        df_used = df

    for _, r in df_used.iterrows():
        name = r.get('name', 'imported')
        email = r.get('email', None)
        dob = r.get('dob', None)
        # insert student (ignore duplicate emails)
        if email:
            cur.execute("INSERT OR IGNORE INTO students (name,email,password,dob) VALUES (?,?,?,?)",
                        (name, email, 'imported', dob))
            cur.execute("SELECT id FROM students WHERE email=?", (email,))
            row = cur.fetchone()
            sid = row[0] if row else None
        else:
            # create a stub student row
            cur.execute("INSERT INTO students (name,email,password,dob) VALUES (?,?,?,?)",
                        (name, f"imported+{pd.util.hash_pandas_object(pd.Series([name])).iloc[0]}@example.invalid", 'imported', dob))
            sid = cur.lastrowid

        if sid is None:
            continue

        values = [sid]
        for c in expected:
            values.append(int(r.get(c, 0)))
        total_score = int(r.get('total_score', sum(values[1:])))
        result = r.get('result', '')

        cur.execute(
            """INSERT INTO test_results (student_id,stress,anxiety,sleep,focus,social,sadness,energy,overwhelm,total_score,result)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            tuple([sid] + values[1:] + [total_score, result])
        )

    conn.commit()
    conn.close()
    print("Import complete.")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--db', default='database.db')
    args = p.parse_args()
    main(args.csv, args.db)
