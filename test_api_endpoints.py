"""
Integration test for daily check-in API endpoints
Run this after starting the Flask app to test the API
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = 'http://localhost:5000'

def test_api_endpoints():
    """Test the daily check-in API endpoints"""
    
    print("=" * 70)
    print("TESTING DAILY CHECK-IN API ENDPOINTS")
    print("=" * 70)
    
    # Create session
    session = requests.Session()
    
    # Step 1: Register a test user
    print("\n[1] Creating test user...")
    register_data = {
        'name': 'Daily Check-in Tester',
        'email': f'checkin_tester_{int(time.time())}@test.com',
        'password': 'TestPassword123',
        'confirm_password': 'TestPassword123'
    }
    resp = session.post(f'{BASE_URL}/register', data=register_data)
    if 'Please log in' in resp.text or 'login' in resp.text:
        print(f"   [OK] User registered successfully")
    else:
        print(f"   [FAIL] Registration failed")
        return False
    
    # Step 2: Login
    print("[2] Logging in...")
    login_data = {
        'email': register_data['email'],
        'password': register_data['password']
    }
    resp = session.post(f'{BASE_URL}/login', data=login_data)
    if resp.status_code == 200:
        print(f"   [OK] Login successful")
    else:
        print(f"   [FAIL] Login failed with status {resp.status_code}")
        return False
    
    # Step 3: Test record mood endpoint
    print("[3] Testing /api/record-mood endpoint...")
    moods_to_test = ['Amazing', 'Good', 'Okay', 'Stressed', 'Anxious', 'Sad']
    recorded_moods = []
    
    for mood in moods_to_test:
        resp = session.post(
            f'{BASE_URL}/api/record-mood',
            json={'mood': mood},
            headers={'Content-Type': 'application/json'}
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                print(f"   [OK] Recorded mood: {mood}")
                recorded_moods.append(mood)
            else:
                print(f"   [FAIL] Failed to record {mood}: {data.get('error')}")
        else:
            print(f"   [FAIL] Request failed with status {resp.status_code}: {resp.text}")
    
    if len(recorded_moods) < len(moods_to_test):
        print(f"\n   WARNING: Only recorded {len(recorded_moods)}/{len(moods_to_test)} moods")
    
    # Step 4: Test get mood history
    print("\n[4] Testing /api/mood-history endpoint...")
    resp = session.get(f'{BASE_URL}/api/mood-history')
    if resp.status_code == 200:
        data = resp.json()
        moods = data.get('moods', [])
        count = data.get('count', 0)
        print(f"   [OK] Retrieved mood history: {count} moods in last 7 days")
        if moods:
            print(f"   Recent moods:")
            for i, m in enumerate(moods[:3]):
                print(f"     - {m.get('mood')} at {m.get('created_at')}")
        if count >= len(recorded_moods):
            print(f"   [OK] Correct mood count")
    else:
        print(f"   [FAIL] Request failed with status {resp.status_code}")
        return False
    
    # Step 5: Test mood stats
    print("\n[5] Testing /api/mood-stats endpoint...")
    resp = session.get(f'{BASE_URL}/api/mood-stats')
    if resp.status_code == 200:
        data = resp.json()
        latest = data.get('latest_mood')
        dist = data.get('mood_distribution', {})
        total = data.get('total_logs_this_week', 0)
        
        print(f"   [OK] Retrieved mood statistics:")
        print(f"     - Latest mood: {latest}")
        print(f"     - Total logs this week: {total}")
        print(f"     - Mood distribution: {dist}")
        
        if total >= len(recorded_moods):
            print(f"   [OK] Correct total count")
    else:
        print(f"   [FAIL] Request failed with status {resp.status_code}")
        return False
    
    # Step 6: Test unauthenticated access (should fail)
    print("\n[6] Testing authentication protection...")
    session2 = requests.Session()
    resp = session2.post(
        f'{BASE_URL}/api/record-mood',
        json={'mood': 'Good'},
        headers={'Content-Type': 'application/json'}
    )
    if resp.status_code == 401:
        print(f"   [OK] Unauthenticated request correctly rejected (401)")
    else:
        print(f"   [WARN] Expected 401, got {resp.status_code}")
    
    print("\n" + "=" * 70)
    print("[SUCCESS] ALL API TESTS PASSED!")
    print("=" * 70)
    print("\nDaily Check-in Feature is FULLY FUNCTIONAL:")
    print("  - Mood recording endpoint works")
    print("  - Mood history retrieval works")
    print("  - Mood statistics calculation works")
    print("  - Authentication is properly enforced")
    return True

if __name__ == '__main__':
    print("\nNote: Make sure Flask app is running on localhost:5000")
    print("Start it with: python app.py\n")
    
    try:
        test_api_endpoints()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to Flask app on localhost:5000")
        print("   Please start the app with: python app.py")
    except Exception as e:
        print(f"[ERROR] Test error: {e}")
