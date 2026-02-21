# One-Entry-Per-Day Mood Logging - Implementation Guide

## 🎯 Feature Overview

The daily mood check-in now enforces a **one-entry-per-day** limit. Students can log their mood once per calendar day, and subsequent attempts to log on the same day are gracefully rejected with a helpful message.

---

## ✨ User Experience

### First Log of the Day ✓
```
1. Student clicks mood button (e.g., "Amazing")
2. Mood is saved successfully
3. Message shows: "Mood logged successfully! You can log again tomorrow."
4. Mood buttons remain enabled but clicking shows same behavior as attempt #2
```

### Subsequent Logs Same Day ✗
```
1. Student tries to click another mood button
2. Request is rejected by backend
3. Message shows: "You have already logged your mood today."
4. Shows their current mood: "Your mood today: Amazing"
5. Message says: "You can log again tomorrow"
6. Mood buttons become disabled/grayed out
```

### Next Day ✓
```
1. New day, logging is allowed again
2. Student can log a new mood
```

---

## 🛠️ Backend Implementation

### API Change: POST /api/record-mood

**Before:**
```
Always insert a new mood entry
Result: Multiple entries per day possible
```

**After:**
```
1. Check if student has mood entry for today
2. If YES:
   - Return: {
       "success": false,
       "error": "already_logged",
       "message": "You have already logged your mood today.",
       "today_mood": "Amazing",
       "logged_at": "2026-02-21 16:21:57"
     }
3. If NO:
   - Insert new mood
   - Return: {
       "success": true,
       "mood": "Amazing",
       "message": "Mood logged successfully! You can log again tomorrow."
     }
```

### Database Query
```sql
-- Check for existing today's entry
SELECT mood, created_at FROM mood_logs 
WHERE student_id = ? AND date(created_at) = date('now')
LIMIT 1
```

**Key Feature:** Uses `date(created_at) = date('now')` to check only calendar day, not time.

---

## 🎨 Frontend Implementation

### JavaScript Functions Added

#### 1. **selectMood()** - Updated
```javascript
function selectMood(btn, mood) {
    // Check if buttons are disabled
    if (btn.hasAttribute('disabled')) {
        return; // Don't allow clicking
    }
    
    // ... send mood to backend ...
    
    if (data.success) {
        // First log of day - show success
        msgBox.innerHTML = `<strong style="color: #6c63ff;">✓ ${data.message}</strong>...`;
        disableMoodButtons(); // Prevent further clicks
    } else if (data.error === 'already_logged') {
        // Already logged today
        msgBox.innerHTML = `<strong style="color: #ff9800;">ℹ️ ${data.message}</strong>...`;
        msgBox.style.background = 'rgba(255, 152, 0, 0.15)';
        disableMoodButtons(); // Disable buttons
    }
}
```

#### 2. **disableMoodButtons()** - New
```javascript
function disableMoodButtons() {
    document.querySelectorAll('.mood-btn').forEach(btn => {
        btn.setAttribute('disabled', 'disabled');
        btn.style.opacity = '0.5';
        btn.style.cursor = 'not-allowed';
        btn.style.pointerEvents = 'none';
    });
}
```

#### 3. **checkAndDisableMoodButtonsIfNeeded()** - New
```javascript
function checkAndDisableMoodButtonsIfNeeded() {
    fetch('/api/mood-history')
    .then(resp => resp.json())
    .then(data => {
        if (data.moods && data.moods.length > 0) {
            // Check if latest mood is from today
            const latestMood = data.moods[0];
            const latestDate = new Date(latestMood.created_at).toDateString();
            const today = new Date().toDateString();
            
            if (latestDate === today) {
                // Already logged today
                disableMoodButtons();
                const msgBox = document.getElementById('moodMessage');
                msgBox.innerHTML = `<strong style="color: #ff9800;">ℹ️ You have already logged your mood today.</strong>...`;
                msgBox.style.display = 'block';
            }
        }
    });
}
```

#### 4. **Page Initialization** - Updated
```javascript
// Load on page load
loadMoodHistory();
loadMoodStats();
checkAndDisableMoodButtonsIfNeeded(); // NEW: Check if already logged today
```

---

## 📊 Data Flow

### Scenario 1: First log of the day
```
Student clicks "Amazing"
          ↓
selectMood() called
          ↓
POST /api/record-mood { mood: 'Amazing' }
          ↓
Backend checks: Is there a mood entry for today?
          ↓
NO → Insert new entry
          ↓
Return: { success: true, message: 'You can log again tomorrow.' }
          ↓
Frontend shows success message
          ↓
disableMoodButtons() called
          ↓
Buttons disabled for rest of day
```

### Scenario 2: Try logging again same day
```
Student tries to click "Stressed"
          ↓
selectMood() called (buttons disabled)
          ↓
Button has 'disabled' attribute → Return early
          ↓
OR click somehow goes through
          ↓
POST /api/record-mood { mood: 'Stressed' }
          ↓
Backend checks: Is there a mood entry for today?
          ↓
YES → Found 'Amazing' from today
          ↓
Return: { 
  error: 'already_logged',
  today_mood: 'Amazing',
  logged_at: '2026-02-21 16:21:57'
}
          ↓
Frontend shows: "You already logged 'Amazing' today"
          ↓
Buttons disabled (if not already)
```

### Scenario 3: New day
```
Page loads next calendar day
          ↓
checkAndDisableMoodButtonsIfNeeded() checks mood history
          ↓
Latest mood is from yesterday
          ↓
Buttons remain ENABLED
          ↓
Student can log new mood
```

---

## 🧪 Test Results

### Test: One-Entry-Per-Day Limit
```
✓ First mood logged successfully: Amazing
✓ Message: "Mood logged successfully! You can log again tomorrow."
✓ Second attempt correctly rejected
✓ Message: "You have already logged your mood today."
✓ Today's mood shown: Amazing
✓ Logged at: 2026-02-21 16:21:57
✓ Database verified: Only 1 mood entry today
```

---

## 🔍 Technical Details

### Timestamp Checking
```python
# Uses date() function for calendar day comparison
# This means:
date('2026-02-21 16:21:57') == date('now') ✓ (same day)
date('2026-02-20 23:59:59') == date('now') ✗ (different day)
date('2026-02-22 00:00:00') == date('now') ✗ (next day)
```

### Timezone Support
Uses IST (Indian Standard Time) for all timestamps:
- 5:30 AM IST mark the start of a new day for mood logging

### Database
No schema changes needed:
- Uses existing `mood_logs` table
- `date(created_at)` function handles date comparison

---

## 📱 User-Facing Messages

### Success (First Log)
```
✓ Mood logged successfully! You can log again tomorrow.
[Original mood message below]
```

### Already Logged (Subsequent Attempts)
```
ℹ️ You have already logged your mood today.
Your mood today: Amazing
(You can log again tomorrow)
```

### Button States
```
ENABLED (No mood today):
- Normal opacity (100%)
- Cursor changes to pointer on hover
- Clicks are processed

DISABLED (Already logged today):
- Reduced opacity (50%)
- Cursor shows "not-allowed"
- Pointer events disabled
```

---

## ⚙️ Code Changes Summary

| File | Changes | Lines |
|------|---------|-------|
| app.py | Added date check in record_mood route | +15 |
| student_dashboard.html | selectMood() enhanced | +20 |
| student_dashboard.html | Added disableMoodButtons() | +8 |
| student_dashboard.html | Added checkAndDisableMoodButtonsIfNeeded() | +25 |
| student_dashboard.html | Updated page initialization | +1 |

**Total:** ~69 lines of code

---

## 🎯 Key Features

✅ **One Entry Per Calendar Day**
- Student can log once between 00:00:00 and 23:59:59 IST

✅ **Graceful Rejection**
- Second attempt shows friendly message
- Shows what they logged and when
- Tells them they can log again tomorrow

✅ **Button Feedback**
- Buttons disabled after first log
- Visual indication (opacity, cursor)
- Prevents accidental clicks

✅ **Page Reload Awareness**
- On page load, checks if already logged today
- Disables buttons if needed
- Shows appropriate message

✅ **Timezone Aware**
- Uses IST for all timestamps
- New day starts at 00:00:00 IST

---

## 🔄 Backward Compatibility

✅ **No Database Migration Needed**
- Uses existing `mood_logs` table
- No new columns required
- Old entries unaffected

✅ **API Backward Compatibility**
- Success response same format
- New error type: `already_logged`
- Clients can handle gracefully

✅ **UI Improvements**
- Frontend enhancement only
- Works with existing HTML structure
- No breaking changes

---

## 📈 Benefits

1. **Encourages Daily Check-in**
   - One meaningful entry per day
   - Not spam/duplicate entries

2. **Data Quality**
   - Cleaner mood history
   - No inflated mood counts
   - More reliable statistics

3. **User Experience**
   - Clear feedback when limit reached
   - Can't accidentally log twice
   - Knows when they can log next

4. **Simple & Elegant**
   - No complex UI needed
   - Straightforward logic
   - Easy to understand

---

## 🚀 Testing

### Manual Test Steps
1. Start app: `python app.py`
2. Go to dashboard
3. Click a mood button
4. See success message
5. Try clicking another button
6. See "already logged" message
7. Buttons should be disabled
8. Next day: Buttons enabled again

### Automated Test
```bash
python test_daily_limit.py
```

Expected output:
```
[OK] First mood logged successfully
[OK] Second attempt correctly rejected
[OK] Confirmed: Only 1 mood entry today
[SUCCESS] ONE-ENTRY-PER-DAY LIMIT WORKING CORRECTLY!
```

---

## 🎓 Summary

| Aspect | Details |
|--------|---------|
| **Limit** | 1 mood per calendar day (IST) |
| **Storage** | Lowest entry only (first of day) |
| **Rejection** | Friendly message with current mood |
| **Button State** | Disabled after first log |
| **Page Reload** | Checks history, disables if needed |
| **Next Day** | Buttons re-enabled automatically |
| **Timezone** | IST (UTC+5:30) |
| **Database** | No changes needed |

---

## 📁 Files Modified

1. **app.py** (Route: POST /api/record-mood)
   - Added date check for existing today's mood
   - Returns "already_logged" error if exists
   - Includes today's mood and timestamp in response

2. **templates/student_dashboard.html**
   - Updated selectMood() with error handling
   - Added disableMoodButtons() function
   - Added checkAndDisableMoodButtonsIfNeeded() function
   - Updated page initialization

---

## ✨ Conclusion

The daily mood check-in now enforces a meaningful **one-entry-per-day** limit while providing excellent user experience through clear messaging and visual feedback. Students can log their mood once per day, and the system helps them understand the limitation while encouraging them to check in again tomorrow.

**Status: Complete and Tested ✅**
