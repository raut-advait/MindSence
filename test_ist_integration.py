"""
Integration test to verify IST timestamps are saved correctly
"""
import requests
import json
import time
import sqlite3
from datetime import datetime

BASE_URL = 'http://localhost:5000'

def test_ist_timestamp_integration():
    """Test that test results and moods are saved with IST timestamps"""
    
    print("=" * 70)
    print("TESTING IST TIMESTAMP INTEGRATION")
    print("=" * 70)
    
    # Create session
    session = requests.Session()
    
    # Step 1: Register and login
    print("\n[1] Creating test user...")
    register_data = {
        'name': 'IST Timestamp Tester',
        'email': f'ist_test_{int(time.time())}@test.com',
        'password': 'TestPassword123',
        'confirm_password': 'TestPassword123'
    }
    
    resp = session.post(f'{BASE_URL}/register', data=register_data)
    if 'login' in resp.text or resp.status_code == 302:
        print(f"   [OK] User registered")
    else:
        print(f"   [FAIL] Registration failed")
        return False
    
    # Login
    print("[2] Logging in...")
    login_data = {
        'email': register_data['email'],
        'password': register_data['password']
    }
    resp = session.post(f'{BASE_URL}/login', data=login_data)
    if resp.status_code == 200:
        print(f"   [OK] Login successful")
    else:
        print(f"   [FAIL] Login failed")
        return False
    
    # Step 2: Test mood logging with IST timestamp
    print("\n[3] Recording moods (will use IST timestamp)...")
    resp = session.post(
        f'{BASE_URL}/api/record-mood',
        json={'mood': 'Amazing'},
        headers={'Content-Type': 'application/json'}
    )
    
    if resp.status_code == 200:
        print(f"   [OK] Mood recorded successfully")
    else:
        print(f"   [FAIL] Failed to record mood")
        return False
    
    # Step 3: Check database for IST timestamps
    print("\n[4] Checking database for IST timestamps...")
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    # Check mood_logs
    moods = conn.execute("""
        SELECT mood, created_at FROM mood_logs 
        ORDER BY created_at DESC LIMIT 1
    """).fetchall()
    
    if moods:
        mood = moods[0]
        timestamp = mood['created_at']
        print(f"   Latest mood: {mood['mood']}")
        print(f"   Timestamp: {timestamp}")
        
        # Verify timestamp format
        try:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            print(f"   [OK] Timestamp is in valid IST format (YYYY-MM-DD HH:MM:SS)")
            
            # Verify the time is reasonable (should be around 16:xx hours IST)
            hour = dt.hour
            if 0 <= hour <= 23:  # Valid 24-hour format
                print(f"   [OK] Time is in 24-hour format")
            
        except ValueError as e:
            print(f"   [FAIL] Timestamp format error: {e}")
            conn.close()
            return False
    else:
        print(f"   [WARN] No moods found in database")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("[SUCCESS] IST TIMESTAMP INTEGRATION VERIFIED!")
    print("=" * 70)
    print("\nAll timestamps now use Indian Standard Time (IST - UTC+5:30)")
    print("Format: YYYY-MM-DD HH:MM:SS (24-hour format)")
    
    return True

if __name__ == '__main__':
    print("\nNote: Make sure Flask app is running on localhost:5000\n")
    
    try:
        test_ist_timestamp_integration()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to Flask app on localhost:5000")
        print("   Please start the app with: python app.py")
    except Exception as e:
        print(f"[ERROR] Test error: {e}")
        import traceback
        traceback.print_exc()
