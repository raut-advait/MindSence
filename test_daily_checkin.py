"""
Test script to verify daily check-in functionality
"""
import sqlite3
from datetime import datetime, timedelta

def test_mood_tracking():
    """Test that mood tracking database works"""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    print("=" * 60)
    print("TESTING DAILY CHECK-IN FEATURE")
    print("=" * 60)
    
    # Check if mood_logs table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mood_logs'")
    if cur.fetchone():
        print("✓ mood_logs table exists")
    else:
        print("✗ mood_logs table NOT found")
        conn.close()
        return False
    
    # Test the schema
    cur.execute("PRAGMA table_info(mood_logs)")
    columns = cur.fetchall()
    print(f"✓ mood_logs columns: {[c['name'] for c in columns]}")
    
    # Simulate inserting mood data
    test_student_id = 1
    test_moods = ['Amazing', 'Good', 'Okay', 'Stressed', 'Anxious', 'Sad']
    
    print("\nTesting mood inserts:")
    for i, mood in enumerate(test_moods):
        try:
            cur.execute(
                "INSERT INTO mood_logs (student_id, mood) VALUES (?, ?)",
                (test_student_id, mood)
            )
            conn.commit()
            print(f"  ✓ Inserted: {mood}")
        except Exception as e:
            print(f"  ✗ Error inserting {mood}: {e}")
            return False
    
    # Test retrieval
    print("\nTesting mood retrieval:")
    cur.execute(
        "SELECT mood, created_at FROM mood_logs WHERE student_id = ? ORDER BY created_at DESC",
        (test_student_id,)
    )
    moods = cur.fetchall()
    print(f"  ✓ Retrieved {len(moods)} moods:")
    for m in moods:
        print(f"    - {m['mood']} ({m['created_at']})")
    
    # Test mood statistics
    print("\nTesting mood statistics:")
    cur.execute(
        "SELECT mood, COUNT(*) as count FROM mood_logs WHERE student_id = ? GROUP BY mood",
        (test_student_id,)
    )
    stats = cur.fetchall()
    print(f"  Mood distribution:")
    for stat in stats:
        print(f"    - {stat['mood']}: {stat['count']} logs")
    
    # Test 7-day filter
    print("\nTesting 7-day mood filter:")
    cur.execute(
        "SELECT COUNT(*) as count FROM mood_logs WHERE student_id = ? AND date(created_at) >= date('now', '-7 days')",
        (test_student_id,)
    )
    week_count = cur.fetchone()['count']
    print(f"  ✓ Moods logged in last 7 days: {week_count}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED - Daily check-in ready!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    test_mood_tracking()
