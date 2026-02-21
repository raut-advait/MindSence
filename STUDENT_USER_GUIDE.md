# Daily Check-in Feature - User Guide & Walkthrough

## 🎯 Feature Overview

The daily check-in feature allows students to **log their daily mood** with a single click and **track their mental wellness** over time. Data is saved to the database for long-term insights.

---

## 👤 For Students

### How to Use the Daily Check-in

#### Step 1: Go to Dashboard
- Log in to MindSense
- Click "Dashboard" in the sidebar
- You'll see the daily check-in section

#### Step 2: Select Your Mood
Find the section: **"How are you feeling today? Daily check-in"**

Six mood options are available:
```
😄 Amazing   😊 Good   😐 Okay   😟 Stressed   😰 Anxious   😢 Sad
```

Click **ONE** of these buttons to record your mood.

#### Step 3: Get Instant Feedback
A personalized message appears:
- **Click Amazing** → "That's wonderful! 🌟 Keep riding that positive energy!"
- **Click Good** → "Great to hear! 😊 A good day is a gift — make the most of it!"
- **Click Okay** → "That's perfectly fine. 🌤️ Consider taking a short walk or break."
- **Click Stressed** → "I hear you. 😟 Try deep breathing for 5 minutes — it helps!"
- **Click Anxious** → "It's okay to feel anxious. 💙 Take one thing at a time."
- **Click Sad** → "I'm sorry you're feeling this way. 💛 Consider talking to someone you trust."

#### Step 4: Check Your History
Below the mood buttons, you'll see: **"Recent Check-ins (Last 7 Days)"**

This displays all moods you've logged in the past week with:
- Mood emoji (quick visual reference)
- Mood text (Amazing, Good, Stressed, etc.)
- Date and time of the check-in

Example:
```
😊 Good - 02/21/2026 2:15 PM
😄 Amazing - 02/21/2026 10:30 AM
😟 Stressed - 02/20/2026 6:45 PM
```

#### Step 5: Get Personalized Wellness Tips
If you've logged **stressed moods** recently, you'll see an alert above the "Daily Tips" section:

```
👋 We noticed some stressed moods this week. 
   Check out our wellness tips below for support!
```

The tips section provides actionable advice like:
- 🌿 Breathe Deeply - 5 deep breaths every hour
- 💤 Sleep 7-9 Hours - Foundation of good mental health
- 🚶 Move Your Body - 20 mins of walking releases endorphins
- 📵 Digital Detox - 30 mins off screens before bed
- 📝 Journal It Out - Write your thoughts to process emotions
- 🤝 Stay Connected - Social bonds protect against depression

---

## 📊 What Happens Behind the Scenes

### When You Click a Mood Button:

1. **Button is highlighted** (visual feedback)
2. **Message appears** (personalized encouragement)
3. **Mood is saved to database** (automatic, no extra action needed)
4. **History is refreshed** (latest mood appears in list)
5. **Stats are analyzed** (app detects stress patterns)
6. **Wellness alert shown** (if applicable)

NO PAGE REFRESH - everything happens instantly!

### Your Data is Stored:
```
Database Entry:
┌─────────────────────────────────────────┐
│ Your Mood: "Amazing"                    │
│ Date: Feb 21, 2026                      │
│ Time: 2:15 PM                           │
│ Status: ✓ Saved                         │
└─────────────────────────────────────────┘
```

### Mood History:
Your check-ins are kept for **7 days** so you can:
- See how your mood changes over time
- Identify stress patterns
- Recognize what helps you feel better
- Share patterns with a counselor if needed

---

## 🎨 Visual Walkthrough

### Dashboard Section Location:
```
┌────────────────────────────────────────────┐
│ Welcome, John! 🌅                          │
│                                            │
│ [Stat Cards: Assessments | Insights...]   │
│                        ⬇️                  │
│ ┌──────────────────────────────────────┐  │
│ │ How are you feeling today?           │  │
│ │ Daily check-in                       │  │
│ │                                      │  │
│ │ [😄] [😊] [😐] [😟] [😰] [😢]      │  │ ← Click here!
│ │                                      │  │
│ │ ✓ That's wonderful! 🌟               │  │ ← Feedback
│ │                                      │  │
│ │ ┌──────────────────────────────────┐ │  │
│ │ │ Recent Check-ins (Last 7 Days)  │ │  │ ← History
│ │ │                                │ │  │  │
│ │ │ 😊 Good (02/21 2:15 PM)        │ │  │  │
│ │ │ 😄 Amazing (02/21 10:30 AM)    │ │  │  │
│ │ │ 😟 Stressed (02/20 6:45 PM)    │ │  │  │
│ │ └──────────────────────────────────┘ │  │
│ └──────────────────────────────────────┘  │
│                                            │
│ 👋 We noticed some stressed moods...      │ ← Alert
│                                            │
│ Mental Health Assessments                 │
│ ...rest of dashboard...                   │
└────────────────────────────────────────────┘
```

---

## ❓ Frequently Asked Questions

### Q: Does my mood data get saved?
**A:** Yes! Every mood you click is automatically saved to the database with a timestamp.

### Q: How long is my data kept?
**A:** Mood history is displayed for the last 7 days. The database keeps all historical data indefinitely.

### Q: Can I change a mood after logging it?
**A:** Currently, no. You can log a new mood (e.g., if your mood changes later in the day), but previous entries can't be edited.

### Q: Who can see my mood data?
**A:** Only you. Your mood data is private and only accessible when you're logged in.

### Q: Do I have to log my mood every day?
**A:** No, it's optional. Log as often as you feel comfortable.

### Q: What if I log the same mood multiple times?
**A:** That's fine! You'll see all entries in your history with different timestamps.

### Q: Can I use this instead of taking an assessment?
**A:** No, they serve different purposes:
- **Daily Check-in:** Quick mood snapshot (1 click)
- **Mental Health Assessment:** Comprehensive evaluation (5-15 questions)

Use both together for best insights!

### Q: What if the history doesn't update?
**A:** Try refreshing the page. If that doesn't work, check your internet connection.

---

## 📈 How to Use Mood Data Effectively

### Track Your Patterns:
- Log a mood every day at the same time
- Notice which activities or situations affect your mood
- Identify your worst days and what triggered them

### Share with Support:
- Show your mood history to a counselor or therapist
- Discuss patterns and trends
- Get personalized advice based on your data

### Correlate with Assessments:
- Compare mood history with test results
- See if stressed moods align with assessment scores
- Use both for comprehensive mental health picture

### Make Positive Changes:
- Notice when wellness tips help
- Document which strategies work for you
- Celebrate when moods improve

---

## 💡 Tips for Best Results

### 1. **Log Consistently**
If possible, check in at the same time each day for accurate patterns.

### 2. **Be Honest**
Select the mood that best represents how you're truly feeling, not how you wish to feel.

### 3. **Context Matters**
Pair check-ins with notes (use the daily tips section to explain what might be affecting you).

### 4. **Track Triggers**
- When stressed moods appear, think about what happened
- When happy moods appear, think about what went right
- Share these insights with someone you trust

### 5. **Use Wellness Tips**
The system recommends tips based on your mood patterns. Actually try them!

### 6. **Review Weekly**
Once a week, look at your history and identify patterns:
- Mood trends (improving or declining?)
- Peak stress times
- What helps you feel better

---

## 🆘 When to Seek Help

If your check-ins show:
- Consistent "Sad" or "Anxious" moods for several days
- Declining mood patterns
- Only negative moods with no positive days
- Urge to harm yourself

**Please reach out:**
- Talk to a school counselor
- Contact a therapist or mental health professional
- Text crisis line (available 24/7)
- Tell a trusted adult

Your mood data can help explain what you're experiencing to professionals.

---

## 🔒 Privacy & Security

- ✅ Your mood data is PRIVATE (only accessible when you're logged in)
- ✅ Data is ENCRYPTED (stored securely)
- ✅ No ads use your mood data
- ✅ Your school knows about this feature but can't see individual entries
- ✅ You own your data

---

## 🎯 Summary: Quick Start Guide

| Step | Action | Result |
|------|--------|--------|
| 1 | Log into dashboard | See mood tracker section |
| 2 | Click one mood button | Instant confirmation message |
| 3 | Mood is saved | Entry in history with timestamp |
| 4 | View recent check-ins | See your 7-day history |
| 5 | Get personalized tips | Wellness advice based on patterns |

**That's it!** Your mental wellness tracking is now active.

---

## 📞 Need Help?

- **Button not working?** Refresh the page
- **History not showing?** Check internet connection
- **Not seeing mood saved?** Check that you're logged in
- **Want to learn more?** Check out the Mental Health Assessments section
- **Need support?** Use the Resources page or talk to school counselor

---

## 🌟 Your Mental Health Matters

Thank you for taking the time to check in with yourself daily. Small moments of self-awareness can lead to big improvements in your mental health. You're doing great!

Remember: Feeling stressed, anxious, or sad is normal. Taking action (like using these tools) shows strength and self-care.

**Keep going! 💪**
