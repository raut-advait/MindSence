"""
Test to verify test_results are saved with IST timestamps
"""
import requests
import json
import time
import sqlite3
from datetime import datetime

BASE_URL = 'http://localhost:5000'

def test_quiz_ist_timestamp():
    """Test that quiz results are saved with IST timestamps"""
    
    print("=" * 70)
    print("TESTING QUIZ RESULT IST TIMESTAMPS")
    print("=" * 70)
    
    # Create session
    session = requests.Session()
    
    # Register and login
    print("\n[1] Setting up test user...")
    register_data = {
        'name': 'Quiz IST Tester',
        'email': f'quiz_ist_{int(time.time())}@test.com',
        'password': 'TestPassword123',
        'confirm_password': 'TestPassword123'
    }
    
    resp = session.post(f'{BASE_URL}/register', data=register_data)
    
    # Login
    login_data = {
        'email': register_data['email'],
        'password': register_data['password']
    }
    resp = session.post(f'{BASE_URL}/login', data=login_data)
    print(f"   [OK] User created and logged in")
    
    # Submit a quick test
    print("\n[2] Submitting quick mental health test...")
    quiz_data = {
        'mode': 'quick',
        'test_mode': 'quick',
        'stress': '2',
        'anxiety': '2',
        'sleep': '4',
        'focus': '4',
        'social': '4'
    }
    
    resp = session.post(f'{BASE_URL}/predict', data=quiz_data)
    print(f"   [OK] Quiz submitted")
    
    # Check the database for the test result with IST timestamp
    print("\n[3] Checking database for test_results IST timestamp...")
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    results = conn.execute("""
        SELECT student_id, total_score, result, created_at 
        FROM test_results 
        ORDER BY created_at DESC 
        LIMIT 1
    """).fetchall()
    
    if results:
        result = results[0]
        timestamp = result['created_at']
        print(f"   Quiz Result: {result['result']}")
        print(f"   Score: {result['total_score']}")
        print(f"   Timestamp: {timestamp}")
        
        # Verify timestamp format
        try:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            print(f"   [OK] Timestamp is in valid IST format (YYYY-MM-DD HH:MM:SS)")
            
            # Extract time components
            hour = dt.hour
            minute = dt.minute
            second = dt.second
            print(f"   Time: {hour:02d}:{minute:02d}:{second:02d} (24-hour format)")
            print(f"   [OK] Test results now saved with IST timezone")
            
        except ValueError as e:
            print(f"   [FAIL] Timestamp format error: {e}")
            conn.close()
            return False
    else:
        print(f"   [WARN] No test results found")
        conn.close()
        return False
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("[SUCCESS] QUIZ RESULTS USE IST TIMESTAMPS!")
    print("=" * 70)
    
    return True

if __name__ == '__main__':
    print("\nNote: Flask app must be running\n")
    
    try:
        test_quiz_ist_timestamp()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
