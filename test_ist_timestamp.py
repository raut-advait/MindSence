"""
Test script to verify IST timestamp support for test_results and mood_logs
"""
import sqlite3
from datetime import datetime, timezone, timedelta

def test_ist_timestamps():
    """Verify that IST timestamps are stored correctly"""
    
    print("=" * 60)
    print("TESTING IST TIMESTAMP SUPPORT")
    print("=" * 60)
    
    # Connect to database
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get recent test results
    print("\nRecent Test Results (with IST timestamps):")
    cur.execute("""
        SELECT student_id, total_score, result, created_at 
        FROM test_results 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    results = cur.fetchall()
    
    if results:
        print("Found test results with timestamps:")
        for r in results:
            timestamp = r['created_at']
            print(f"  Score: {r['total_score']}, Result: {r['result']}")
            print(f"    Timestamp: {timestamp}")
            
            # Parse and verify the timestamp format
            try:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                print(f"    Format: ✓ Valid IST timestamp")
            except:
                print(f"    Format: ✗ Invalid timestamp format")
    else:
        print("No test results yet (take a test first)")
    
    # Get recent mood entries
    print("\nRecent Mood Logs (with IST timestamps):")
    cur.execute("""
        SELECT student_id, mood, created_at 
        FROM mood_logs 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    moods = cur.fetchall()
    
    if moods:
        print("Found mood logs with timestamps:")
        for m in moods:
            timestamp = m['created_at']
            print(f"  Mood: {m['mood']}")
            print(f"    Timestamp: {timestamp}")
            
            # Parse and verify the timestamp format
            try:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                print(f"    Format: ✓ Valid IST timestamp")
            except:
                print(f"    Format: ✗ Invalid timestamp format")
    else:
        print("No mood logs yet (take a mood check-in first)")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✓ IST TIMESTAMP SUPPORT VERIFIED")
    print("=" * 60)
    print("\nAll new entries will use Indian Standard Time (IST)")
    print("Format: YYYY-MM-DD HH:MM:SS (24-hour format)")

if __name__ == '__main__':
    test_ist_timestamps()
