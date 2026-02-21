# Daily Check-in Feature - Quick Start Guide

## 🚀 Get Started in 2 Minutes

This guide will get you up and running with the newly implemented daily check-in feature.

---

## Step 1: Start the App (1 minute)

Open a terminal in the project directory:

```bash
python app.py
```

You should see:
```
 * Running on http://localhost:5000
 * Debug mode: on
```

The app is now running! Leave this terminal open.

---

## Step 2: Open in Browser (30 seconds)

Open your web browser and go to:
```
http://localhost:5000
```

You'll see the MindSense home page.

---

## Step 3: Register & Login (1 minute)

1. Click "Register" or "Sign Up"
2. Fill in your details:
   - Name: (your name)
   - Email: test@example.com
   - Password: TestPassword123
3. Click "Register"
4. Login with the same credentials

You're now on the dashboard!

---

## Step 4: Try the Daily Check-in (30 seconds)

1. Scroll down to **"How are you feeling today?"** section
2. Click one of the mood buttons:
   - 😄 Amazing
   - 😊 Good
   - 😐 Okay  
   - 😟 Stressed
   - 😰 Anxious
   - 😢 Sad

3. See the instant feedback message
4. Look below - your mood appears in the "Recent Check-ins" section!

---

## Step 5: Test More Features (1 minute)

### Click Multiple Moods
Click several different mood buttons. Watch them all appear in the history!

### Refresh the Page
Reload the page - your moods are still there! Data persists.

### View the Daily Tips
Scroll down to the "Daily Tips" section. 

If you logged any stressed moods, you'll see an alert:
```
👋 We noticed some stressed moods this week. 
   Check out our wellness tips below for support!
```

---

## 📱 What You're Looking At

### The Mood Tracker Section:
```
┌─────────────────────────────────────────────┐
│ How are you feeling today? Daily check-in   │
│                                             │
│ [😄] [😊] [😐] [😟] [😰] [😢]           │
│                                             │
│ ↓ (Click one)                               │
│ ✓ That's wonderful! 🌟 Keep riding...      │
│                                             │
│ Recent Check-ins (Last 7 Days)              │
│ ┌────────────────────────────────┐          │
│ │ 😊 Good (2:15 PM)             │          │
│ │ 😄 Amazing (10:30 AM)         │          │
│ │ 😟 Stressed (Yesterday 6:45 PM) │       │
│ └────────────────────────────────┘          │
│                                             │
│ 👋 We noticed some stressed moods...        │
└─────────────────────────────────────────────┘
```

---

## 🧪 Advanced: Test the API

Open a **new terminal** (keep Flask running in the first one):

```bash
python test_api_endpoints.py
```

You'll see comprehensive API tests:
```
[1] Creating test user...
   [OK] User registered successfully
[2] Logging in...
   [OK] Login successful
[3] Testing /api/record-mood endpoint...
   [OK] Recorded mood: Amazing
   [OK] Recorded mood: Good
   ...

[SUCCESS] ALL API TESTS PASSED!
```

This verifies the backend is working perfectly.

---

## 🗄️ Advanced: Check the Database

Open a **new terminal**:

```bash
python -c "
import sqlite3
conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT * FROM mood_logs ORDER BY created_at DESC LIMIT 5').fetchall()
print('Recent Mood Logs:')
for row in rows:
    print(f'  {dict(row)}')
"
```

You'll see your recorded moods in the database!

---

## 📊 What Just Happened?

You successfully:
1. ✅ Started the Flask app
2. ✅ Registered as a student
3. ✅ Logged the daily mood tracker
4. ✅ Recorded multiple moods
5. ✅ Viewed persistent history
6. ✅ Got personalized feedback
7. ✅ Saw mood-based wellness alerts
8. ✅ Verified data in database

**The daily check-in feature is fully functional!**

---

## 🔍 Features to Explore

### 1. Real-time Updates
- Click mood → See it appear in history immediately
- No page refresh needed
- Happens in milliseconds

### 2. 7-Day History
- Each mood shows mood emoji, text, date, and time
- Most recent at the top
- Can see patterns across multiple days

### 3. Personalized Messages
Try each mood and see the different messages:
- 😄 Amazing → "Keep riding that positive energy!"
- 😊 Good → "Make the most of it!"
- 😐 Okay → "Consider taking a short walk"
- 😟 Stressed → "Try deep breathing"
- 😰 Anxious → "Take one thing at a time"
- 😢 Sad → "Consider talking to someone you trust"

### 4. Stress Detection
- Log 2-3 stressed/anxious moods
- Reload the page
- See the wellness alert appear!

### 5. Wellness Tips
- Scroll to "Daily Tips" section
- See relevant wellness advice
- Tips adjust based on your mood patterns

---

## 📚 Learn More

Read these documents in order:

1. **[DAILY_CHECKIN_IMPLEMENTATION.md](DAILY_CHECKIN_IMPLEMENTATION.md)** ← Start here for overview
   - What was built
   - How students use it
   - API reference

2. **[CODE_CHANGES_REFERENCE.md](CODE_CHANGES_REFERENCE.md)** ← For developers
   - Exact code modifications
   - Database schema
   - Implementation details

3. **[STUDENT_USER_GUIDE.md](STUDENT_USER_GUIDE.md)** ← For student instructions
   - How to use the feature
   - FAQs
   - Tips for getting the most out of it

4. **[DAILY_CHECKIN_GUIDE.md](DAILY_CHECKIN_GUIDE.md)** ← Technical deep-dive
   - Architecture
   - Security
   - Complete API documentation

5. **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)** ← Project status
   - What's complete
   - What's tested
   - Deployment readiness

---

## ❓ Quick Troubleshooting

### Mood not saving?
1. Check you're logged in
2. Check browser console (F12)
3. Restart Flask app
4. Refresh page

### History not showing?
1. Refresh the page
2. Check internet connection
3. Clear browser cache
4. Verify Flask is running

### Getting 401 error?
1. Log out and log back in
2. Clear browser cookies
3. Check that Flask app is running

### Database not found?
1. Make sure you're in the project directory
2. Run `python init_db.py` to create database
3. Then run `python app.py`

---

## 🎯 Try These Variations

### Variation 1: Multiple Users
1. Open browser A: Login as user1@test.com
2. In another browser/incognito: Login as user2@test.com
3. Each logs their own moods
4. Each sees only their own history (complete isolation!)

### Variation 2: 7-Day View
1. Record moods for several days
2. Wait for page to show 7-day history
3. See patterns emerge
4. Correlate with real-life events

### Variation 3: Stress Pattern Detection
1. Log "Stressed" moods a few times
2. Refresh the page
3. See the wellness alert appear
4. This is automatic mood analysis!

### Variation 4: API Testing
See [test_api_endpoints.py](test_api_endpoints.py) for full integration tests.

---

## 🚀 Next Steps

### For Deployment:
1. Review [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
2. Run full test suite
3. Deploy to production
4. Monitor for errors

### For Enhancement:
1. Add mood trends visualization
2. Add mood-based resource recommendations
3. Add mood reminders/notifications
4. Add mood data export

### For Integration:
1. Link moods with assessment results
2. Show mood correlation with mental health scores
3. Create mood-based intervention suggestions
4. Build mood trend reports

---

## 📞 Questions?

Look for answers in:
- **API Questions** → [DAILY_CHECKIN_GUIDE.md](DAILY_CHECKIN_GUIDE.md)
- **Code Questions** → [CODE_CHANGES_REFERENCE.md](CODE_CHANGES_REFERENCE.md)
- **User Questions** → [STUDENT_USER_GUIDE.md](STUDENT_USER_GUIDE.md)
- **Status Questions** → [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)

---

## ✅ Completion Checklist

After completing this quick start:

- [ ] Flask app is running on localhost:5000
- [ ] I can register and login
- [ ] I can click mood buttons
- [ ] Moods appear in history
- [ ] History persists after refresh
- [ ] Personalized messages display
- [ ] Wellness alert shows for stressed moods
- [ ] API tests pass
- [ ] Database contains mood records

If all checkboxes are complete: **You're all set! 🎉**

---

## 🎓 What You Learned

- How to use the daily check-in feature
- How to test API endpoints
- How to verify database storage
- How to check multiple users
- How to troubleshoot common issues
- Where to find complete documentation

**The feature is production-ready and fully tested!**

---

## 🌟 Summary

You now have a **fully functional daily mood check-in system** that:
- Stores moods persistently in database
- Shows 7-day mood history
- Detects stress patterns
- Provides personalized wellness tips
- Has secure authentication
- Is thoroughly tested and documented

Perfect for tracking student mental wellness! 💚
