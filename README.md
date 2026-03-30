# MindSense - Student Mental Health Analyzer

Flask + PostgreSQL application for student mental wellness screening with quick/full assessments, mood logs, analytics dashboards, and AI-generated summaries.

## Current production behavior

- Authentication: register, login, logout
- Quick assessment: severity-oriented quick check-in flow
- Full assessment: 10-question severity-aligned flow
- Mood logging: one log per day (strict mode)
- Dashboards: History + Analytics (charts, trends, paginated tables)
- AI features: analytics summary + assistant chat (Groq)

## Runtime architecture

- Backend: `app.py` + `db_helpers.py`
- Database: PostgreSQL (`DATABASE_URL` required)
- Models loaded at runtime:
    - `models/quick_model.pkl` + `models/quick_preprocessor.pkl`
    - `models/severity_model.pkl` + `models/severity_preprocessor.pkl`
- Frontend: server-rendered Jinja templates in `templates/`

## Required environment variables

- `DATABASE_URL` (required)
- `FLASK_SECRET` (required in production)
- `GROQ_API_KEY` (required for AI summary/chat)
- `GROQ_MODEL` (optional, default: `llama-3.1-8b-instant`)

## Local run (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:DATABASE_URL="postgresql://postgres:password@localhost:5432/mental_health_dev"
$env:FLASK_SECRET="replace-with-random-secret"
$env:GROQ_API_KEY="replace-with-groq-key"

python app.py
```

Open http://127.0.0.1:5000

## Disclaimer

This project is a wellness screening tool and not a medical diagnosis system.
