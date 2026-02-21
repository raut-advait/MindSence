"""
Test script to verify one-entry-per-day mood logging
"""
import requests
import json
import time

BASE_URL = 'http://localhost:5000'

def test_one_entry_per_day():
    """Test that only one mood entry per day is allowed"""
    
    print("=" * 70)
    print("TESTING ONE-ENTRY-PER-DAY MOOD LIMIT")
    print("=" * 70)
    
    # Create session
    session = requests.Session()
    
    # Step 1: Register and login
    print("\n[1] Creating test user...")
    register_data = {
        'name': 'Daily Limit Tester',
        'email': f'daily_limit_{int(time.time())}@test.com',
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
    
    # Step 2: Log mood first time (should succeed)
    print("\n[3] Attempt 1: Log mood 'Amazing'...")
    resp = session.post(
        f'{BASE_URL}/api/record-mood',
        json={'mood': 'Amazing'},
        headers={'Content-Type': 'application/json'}
    )
    data = resp.json()
    
    if resp.status_code == 200 and data.get('success'):
        print(f"   [OK] First mood logged successfully: {data.get('mood')}")
        print(f"   Message: {data.get('message')}")
    else:
        print(f"   [FAIL] First mood logging failed")
        return False
    
    # Step 3: Try to log another mood same day (should be rejected)
    print("\n[4] Attempt 2: Try logging mood 'Stressed' (same day)...")
    
    # Small delay to ensure it's a "different" request
    time.sleep(1)
    
    resp = session.post(
        f'{BASE_URL}/api/record-mood',
        json={'mood': 'Stressed'},
        headers={'Content-Type': 'application/json'}
    )
    data = resp.json()
    
    if resp.status_code == 200 and not data.get('success') and data.get('error') == 'already_logged':
        print(f"   [OK] Second attempt correctly rejected!")
        print(f"   Message: {data.get('message')}")
        print(f"   Today's mood: {data.get('today_mood')}")
        print(f"   Response: You already logged '{data.get('today_mood')}' today at {data.get('logged_at')}")
    else:
        print(f"   [FAIL] Second attempt was not rejected as expected")
        print(f"   Response: {data}")
        return False
    
    # Step 4: Verify only one entry exists today
    print("\n[5] Verifying database has only one entry for today...")
    resp = session.get(f'{BASE_URL}/api/mood-history')
    data = resp.json()
    
    # Count moods from today
    from datetime import datetime
    today = datetime.now().date()
    today_moods = 0
    for mood in data.get('moods', []):
        mood_date = datetime.strptime(mood['created_at'], '%Y-%m-%d %H:%M:%S').date()
        if mood_date == today:
            today_moods += 1
    
    if today_moods == 1:
        print(f"   [OK] Confirmed: Only 1 mood entry today ('{data['moods'][0]['mood']}')")
    else:
        print(f"   [FAIL] Expected 1 mood today, found {today_moods}")
        return False
    
    print("\n" + "=" * 70)
    print("[SUCCESS] ONE-ENTRY-PER-DAY LIMIT WORKING CORRECTLY!")
    print("=" * 70)
    print("\nFeature Behavior:")
    print("  - First mood of the day: Logged successfully")
    print("  - Subsequent attempts same day: Rejected with message")
    print("  - Shows today's logged mood")
    print("  - Tells user they can log again tomorrow")
    
    return True

if __name__ == '__main__':
    print("\nNote: Make sure Flask app is running on localhost:5000\n")
    
    try:
        test_one_entry_per_day()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to Flask app on localhost:5000")
        print("   Please start the app with: python app.py")
    except Exception as e:
        print(f"[ERROR] Test error: {e}")
        import traceback
        traceback.print_exc()
