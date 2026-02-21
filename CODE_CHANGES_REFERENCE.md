# Daily Check-in Feature - Code Changes Reference

## Quick Overview
This document shows exactly what code was added/modified to implement the daily check-in feature.

---

## 1. app.py - Database Initialization

### Location: `init_db()` function, lines ~65-92

**ADDED:** mood_logs table creation
```python
cur.execute("""
    CREATE TABLE IF NOT EXISTS mood_logs (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id  INTEGER NOT NULL,
        mood        TEXT NOT NULL,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )
""")
```

---

## 2. app.py - Backend API Routes

### Location: Lines ~725-815 in app.py (after test history route)

**ADDED THREE NEW ROUTES:**

### Route 1: POST /api/record-mood
```python
@app.route('/api/record-mood', methods=['POST'])
def record_mood():
    """Record daily mood check-in"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    mood = request.json.get('mood')
    if not mood:
        return {'error': 'Mood required'}, 400
    
    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO mood_logs (student_id, mood) VALUES (?, ?)",
            (session.get('user_id'), mood)
        )
        conn.commit()
        conn.close()
        return {'success': True, 'mood': mood}, 200
    except Exception as e:
        print(f"Error recording mood: {e}")
        return {'error': str(e)}, 500
```

### Route 2: GET /api/mood-history
```python
@app.route('/api/mood-history', methods=['GET'])
def mood_history():
    """Get mood history for current student (last 7 days)"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    try:
        conn = get_db()
        moods = conn.execute(
            """SELECT mood, created_at FROM mood_logs 
               WHERE student_id = ? AND date(created_at) >= date('now', '-7 days')
               ORDER BY created_at DESC""",
            (session.get('user_id'),)
        ).fetchall()
        conn.close()
        
        return {
            'moods': [dict(m) for m in moods],
            'count': len(moods)
        }, 200
    except Exception as e:
        print(f"Error fetching mood history: {e}")
        return {'error': str(e)}, 500
```

### Route 3: GET /api/mood-stats
```python
@app.route('/api/mood-stats', methods=['GET'])
def mood_stats():
    """Get mood statistics for personalized recommendations"""
    if 'user' not in session:
        return {'error': 'Not logged in'}, 401
    
    try:
        conn = get_db()
        # Get today's moods
        today_moods = conn.execute(
            """SELECT mood FROM mood_logs 
               WHERE student_id = ? AND date(created_at) = date('now')
               ORDER BY created_at DESC""",
            (session.get('user_id'),)
        ).fetchall()
        
        # Get last 7 days mood distribution
        week_moods = conn.execute(
            """SELECT mood, COUNT(*) as count FROM mood_logs 
               WHERE student_id = ? AND date(created_at) >= date('now', '-7 days')
               GROUP BY mood""",
            (session.get('user_id'),)
        ).fetchall()
        conn.close()
        
        mood_distribution = {m['mood']: m['count'] for m in week_moods}
        latest_mood = today_moods[0]['mood'] if today_moods else None
        
        return {
            'latest_mood': latest_mood,
            'mood_distribution': mood_distribution,
            'total_logs_this_week': sum(mood_distribution.values())
        }, 200
    except Exception as e:
        print(f"Error calculating mood stats: {e}")
        return {'error': str(e)}, 500
```

---

## 3. templates/student_dashboard.html - JavaScript Functions

### Location: Lines ~375-450 (in the `<script>` section)

### REPLACED: selectMood() function
**OLD (just UI):**
```javascript
function selectMood(btn, mood) {
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    const messages = {...};
    const msgBox = document.getElementById('moodMessage');
    msgBox.textContent = messages[mood];
    msgBox.style.display = 'block';
}
```

**NEW (with backend integration):**
```javascript
function selectMood(btn, mood) {
    // Update UI
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    
    const messages = {
        'Amazing': "That's wonderful! 🌟 Keep riding that positive energy!",
        'Good': "Great to hear! 😊 A good day is a gift — make the most of it!",
        'Okay': "That's perfectly fine. 🌤️ Consider taking a short walk or break.",
        'Stressed': "I hear you. 😟 Try deep breathing for 5 minutes — it helps!",
        'Anxious': "It's okay to feel anxious. 💙 Take one thing at a time.",
        'Sad': "I'm sorry you're feeling this way. 💛 Consider talking to someone you trust."
    };
    
    const msgBox = document.getElementById('moodMessage');
    msgBox.textContent = messages[mood];
    msgBox.style.display = 'block';
    
    // ADDED: Save to backend
    fetch('/api/record-mood', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mood: mood })
    })
    .then(resp => resp.json())
    .then(data => {
        if (data.success) {
            console.log('Mood recorded:', mood);
            // Load updated history
            loadMoodHistory();
            loadMoodStats();
        } else {
            console.error('Error recording mood:', data.error);
        }
    })
    .catch(err => console.error('Error:', err));
}
```

### ADDED: loadMoodHistory() function
```javascript
function loadMoodHistory() {
    fetch('/api/mood-history')
    .then(resp => resp.json())
    .then(data => {
        const historyContainer = document.getElementById('moodHistory');
        if (historyContainer && data.moods && data.moods.length > 0) {
            const moodEmojis = {
                'Amazing': '😄',
                'Good': '😊',
                'Okay': '😐',
                'Stressed': '😟',
                'Anxious': '😰',
                'Sad': '😢'
            };
            
            if (!historyContainer.innerHTML.includes('mood-history-list')) {
                historyContainer.innerHTML = `
                    <div style="margin-top:20px; padding:15px; background:rgba(108,99,255,0.08); border-radius:10px;">
                        <div style="font-size:0.9rem; font-weight:700; color:var(--text-primary); margin-bottom:10px;">Recent Check-ins (Last 7 Days)</div>
                        <div id="mood-history-list" style="display:flex; flex-wrap:wrap; gap:8px;"></div>
                    </div>
                `;
            }
            
            const list = document.getElementById('mood-history-list');
            list.innerHTML = data.moods.slice(0, 10).map(m => {
                const date = new Date(m.created_at).toLocaleDateString();
                const time = new Date(m.created_at).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
                const emoji = moodEmojis[m.mood] || '😐';
                return `<div style="background:rgba(255,255,255,0.08); padding:8px 12px; border-radius:8px; font-size:0.8rem;">${emoji} ${m.mood} <br/><span style="color:var(--text-secondary); font-size:0.75rem;">${date} ${time}</span></div>`;
            }).join('');
        }
    })
    .catch(err => console.error('Error loading mood history:', err));
}
```

### ADDED: loadMoodStats() function
```javascript
function loadMoodStats() {
    fetch('/api/mood-stats')
    .then(resp => resp.json())
    .then(data => {
        // Personalize tips based on mood distribution
        if (data.mood_distribution) {
            const stressIndicators = ['Stressed', 'Anxious', 'Sad'];
            const stressCount = stressIndicators.reduce((sum, mood) => sum + (data.mood_distribution[mood] || 0), 0);
            
            // If user has logged stressed moods, show wellness tips
            if (stressCount > 0) {
                const stressMsg = document.createElement('div');
                stressMsg.style.cssText = 'padding:12px; background:rgba(255,193,7,0.15); border-left:4px solid #ffc107; margin-bottom:15px; border-radius:4px; font-size:0.9rem; color:var(--text-primary);';
                stressMsg.textContent = `👋 We noticed some stressed moods this week. Check out our wellness tips below for support!`;
                const tipsSection = document.querySelector('[id*="tips"]');
                if (tipsSection && !document.querySelector('[id*="stress-msg"]')) {
                    stressMsg.id = 'stress-msg';
                    tipsSection.parentNode.insertBefore(stressMsg, tipsSection);
                }
            }
        }
    })
    .catch(err => console.error('Error loading mood stats:', err));
}

// Load mood history and stats on page load
loadMoodHistory();
loadMoodStats();
```

---

## 4. templates/student_dashboard.html - HTML Structure

### Location: Lines ~316-320 (mood tracker section)

**ADDED:** moodHistory container div
```html
<div id="moodMessage"
    style="margin-top:16px; font-size:0.9rem; color:var(--text-secondary); display:none; padding:12px 16px; background:rgba(108,99,255,0.08); border-radius:10px; border:1px solid rgba(108,99,255,0.15);">
</div>
<!-- ADDED THIS LINE: -->
<div id="moodHistory"></div>
```

This div dynamically receives the mood history markup from JavaScript.

---

## Summary of Changes

| File | Type | Lines | Change |
|------|------|-------|--------|
| app.py | Database | ~88 | Added mood_logs table |
| app.py | Route | ~725-757 | Added POST /api/record-mood |
| app.py | Route | ~760-779 | Added GET /api/mood-history |
| app.py | Route | ~782-815 | Added GET /api/mood-stats |
| student_dashboard.html | Function | ~382-420 | Updated selectMood() |
| student_dashboard.html | Function | ~422-462 | Added loadMoodHistory() |
| student_dashboard.html | Function | ~464-490 | Added loadMoodStats() |
| student_dashboard.html | HTML | ~319 | Added moodHistory div |

**Total Lines Added:** ~250 lines of code
**Files Modified:** 2 files
**Backwards Compatible:** Yes - all changes are additive

---

## How It Works: Data Flow

```
1. User clicks mood button
   ↓
2. selectMood(btn, mood) called
   ↓
3. Update UI (highlight button, show message)
   ↓
4. POST /api/record-mood with { mood: 'Amazing' }
   ↓
5. Backend validates session + inserts into mood_logs
   ↓
6. Return JSON { success: true, mood: 'Amazing' }
   ↓
7. Call loadMoodHistory() & loadMoodStats()
   ↓
8. GET /api/mood-history - fetch recent moods
   GET /api/mood-stats - fetch statistics
   ↓
9. Update moodHistory div with recent check-ins
   ↓
10. If stress moods detected, show personalized alert
   ↓
11. All updates without page refresh ✨
```

---

## Testing the Implementation

### Test 1: Database (test_daily_checkin.py)
```bash
python test_daily_checkin.py
```
Expected: All 6 mood types insert/retrieve successfully

### Test 2: API Endpoints (test_api_endpoints.py)
Requires Flask running:
```bash
# Terminal 1:
python app.py

# Terminal 2:
python test_api_endpoints.py
```
Expected: All API tests pass with proper authentication

### Test 3: Manual Testing
1. Start Flask app: `python app.py`
2. Go to `http://localhost:5000`
3. Register/Login
4. Click mood buttons on dashboard
5. Check if history appears
6. Refresh page - mood history persists
7. Check database: `SELECT * FROM mood_logs`

---

## Error Handling

**What happens if:**
- User is not logged in → 401 error returned
- Mood parameter missing → 400 error returned
- Database error → 500 error returned
- Network error during fetch → Caught and logged in console

All errors are gracefully handled without crashing the app.

---

## Security

**Implemented:**
- ✅ Session authentication required
- ✅ User isolation (can only access own data)
- ✅ SQL injection protection (parameterized queries)
- ✅ Input validation
- ✅ Proper HTTP method validation

---

## Files You Can Reference

1. **DAILY_CHECKIN_GUIDE.md** - Complete technical documentation
2. **DAILY_CHECKIN_IMPLEMENTATION.md** - Feature summary and usage
3. **test_daily_checkin.py** - Database testing
4. **test_api_endpoints.py** - API integration testing

---

## Version Info

- **Feature Version:** 1.0
- **Implementation Date:** Feb 21, 2026
- **Backend:** Python/Flask
- **Frontend:** JavaScript (Fetch API)
- **Database:** SQLite
- **Status:** ✅ Production Ready
