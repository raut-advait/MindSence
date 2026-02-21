"""
Add 2 weeks of test data for rohan1234@gmail.com
Creates realistic test entries with varying scores across different mental health categories
"""

import sqlite3
from datetime import datetime, timedelta
import random

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def analyze_score(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm):
    """Analyze score and return category"""
    total = stress + anxiety + sleep + focus + social + sadness + energy + overwhelm
    
    if total <= 10:
        return "Excellent Mental Well-being"
    elif total <= 20:
        return "Moderate Stress Detected"
    elif total <= 30:
        return "High Stress & Anxiety"
    else:
        return "Severe Distress Detected"

def add_test_data():
    """Add 14 days of test data for rohan"""
    conn = get_db()
    cur = conn.cursor()
    
    # Get rohan's student ID
    cur.execute("SELECT id FROM students WHERE email = ?", ("rohan1234@gmail.com",))
    student = cur.fetchone()
    
    if not student:
        print("❌ Student rohan1234@gmail.com not found!")
        return
    
    student_id = student[0]
    print(f"✓ Found student: rohan (ID: {student_id})")
    
    # Generate test data for 14 days (starting from today going back 14 days)
    test_data = [
        # Day 1 - Moderate stress
        {"date": -13, "stress": 3, "anxiety": 3, "sleep": 2, "focus": 1, "social": 2, "sadness": 1, "energy": 3, "overwhelm": 2},
        
        # Day 2 - High stress
        {"date": -12, "stress": 4, "anxiety": 4, "sleep": 1, "focus": 2, "social": 1, "sadness": 3, "energy": 2, "overwhelm": 4},
        
        # Day 3 - Excellent
        {"date": -10, "stress": 1, "anxiety": 1, "sleep": 1, "focus": 1, "social": 1, "sadness": 0, "energy": 2, "overwhelm": 1},
        
        # Day 4 - Moderate
        {"date": -9, "stress": 2, "anxiety": 2, "sleep": 2, "focus": 2, "social": 2, "sadness": 1, "energy": 2, "overwhelm": 2},
        
        # Day 5 - High stress
        {"date": -8, "stress": 3, "anxiety": 4, "sleep": 2, "focus": 1, "social": 1, "sadness": 2, "energy": 1, "overwhelm": 4},
        
        # Day 6 - Moderate
        {"date": -7, "stress": 2, "anxiety": 3, "sleep": 2, "focus": 2, "social": 2, "sadness": 1, "energy": 2, "overwhelm": 2},
        
        # Day 7 - Excellent
        {"date": -6, "stress": 1, "anxiety": 1, "sleep": 2, "focus": 1, "social": 2, "sadness": 0, "energy": 3, "overwhelm": 1},
        
        # Day 8 - Moderate
        {"date": -5, "stress": 2, "anxiety": 2, "sleep": 2, "focus": 1, "social": 2, "sadness": 1, "energy": 2, "overwhelm": 2},
        
        # Day 9 - High stress (rough day)
        {"date": -4, "stress": 4, "anxiety": 3, "sleep": 1, "focus": 1, "social": 1, "sadness": 3, "energy": 1, "overwhelm": 3},
        
        # Day 10 - Moderate improving
        {"date": -3, "stress": 3, "anxiety": 2, "sleep": 2, "focus": 2, "social": 2, "sadness": 1, "energy": 2, "overwhelm": 2},
        
        # Day 11 - Moderate
        {"date": -2, "stress": 2, "anxiety": 2, "sleep": 2, "focus": 2, "social": 2, "sadness": 1, "energy": 3, "overwhelm": 1},
        
        # Day 12 - Excellent
        {"date": -1, "stress": 1, "anxiety": 1, "sleep": 2, "focus": 1, "social": 3, "sadness": 0, "energy": 3, "overwhelm": 1},
        
        # Day 13 - Moderate
        {"date": 0, "stress": 2, "anxiety": 2, "sleep": 2, "focus": 2, "social": 2, "sadness": 1, "energy": 2, "overwhelm": 2},
    ]
    
    # Insert test data
    added_count = 0
    for test in test_data:
        date_offset = test.pop("date")
        test_date = datetime.now() + timedelta(days=date_offset)
        timestamp = test_date.strftime("%Y-%m-%d %H:%M:%S")
        
        stress = test["stress"]
        anxiety = test["anxiety"]
        sleep = test["sleep"]
        focus = test["focus"]
        social = test["social"]
        sadness = test["sadness"]
        energy = test["energy"]
        overwhelm = test["overwhelm"]
        
        total_score = stress + anxiety + sleep + focus + social + sadness + energy + overwhelm
        result = analyze_score(stress, anxiety, sleep, focus, social, sadness, energy, overwhelm)
        
        cur.execute("""
            INSERT INTO test_results (student_id, stress, anxiety, sleep, focus, social, sadness, energy, overwhelm, total_score, result, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, stress, anxiety, sleep, focus, social, sadness, energy, overwhelm, total_score, result, timestamp))
        
        added_count += 1
        date_str = test_date.strftime("%Y-%m-%d")
        category_emoji = {
            "Excellent Mental Well-being": "✅",
            "Moderate Stress Detected": "⚠️",
            "High Stress & Anxiety": "🔴",
            "Severe Distress Detected": "🚨"
        }.get(result, "❓")
        
        print(f"  ✓ {date_str}: Score {total_score}/40 {category_emoji} {result.split(' ')[0]}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Successfully added {added_count} test entries!")
    print(f"📊 History page will now show 2 weeks of mental health tracking data")

if __name__ == "__main__":
    add_test_data()
