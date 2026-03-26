# MindSense — Student Mental Health Analyzer

Production-ready Flask application for student wellness screening, mood tracking, assessment history, and AI-assisted insights.

## What this app includes

- Student authentication (register/login/logout)
- Quick and full mental wellness assessments
- Lifestyle-model risk prediction (XGBoost-based artifact)
- Mood check-ins and history APIs
- Analytics dashboard + AI summary/chat endpoints (Groq)
- PostgreSQL-backed persistence

## Current project structure

```
student_mental_health_analyzer/
├── app.py
├── db_helpers.py
├── requirements.txt
├── README.md
├── .env.local                 # local-only; do not commit real secrets
├── data/
│   └── student_lifestyle_100k.csv
├── models/
│   ├── trained_model.pkl
│   ├── preprocessor.pkl
│   ├── metadata.json
│   └── features.json
├── scripts/
│   ├── trained_model.py
│   └── evaluate_lifestyle_model.py
├── static/
│   ├── style.css
│   ├── theme.js
│   └── favicon.svg
└── templates/
        ├── home.html
        ├── login.html
        ├── register.html
        ├── student_dashboard.html
        ├── test.html
        ├── result.html
        ├── history.html
        ├── daily_tips.html
        ├── resources.html
        └── analytics.html
```

## Runtime requirements

- Python 3.10+
- PostgreSQL database
- Environment variables:
    - `DATABASE_URL` (required)
    - `FLASK_SECRET` (required for production)
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

Open `http://127.0.0.1:5000`.

## Deploy on Render (Web Service)

1. Push repository to GitHub.
2. In Render, create a new **Web Service** from that repo.
3. Set:
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add environment variables in Render:
     - `DATABASE_URL` = Render PostgreSQL internal URL
     - `FLASK_SECRET` = strong random value
     - `GROQ_API_KEY` = your Groq API key
     - `GROQ_MODEL` = optional override
5. Deploy.

### Deploy via Blueprint (Optional)

This repo includes `render.yaml` for one-click Blueprint setup in Render.

With Blueprint, a managed PostgreSQL service is provisioned and `DATABASE_URL` is auto-wired to the web service.
You only need to set secret env vars (`FLASK_SECRET`, `GROQ_API_KEY`) in Render.

### Notes for Render

- `init_db()` now runs at app startup, so required tables are initialized under Gunicorn.
- Do not rely on `.env.local` in Render; use Render Environment settings.
- Use `.env.example` as the safe template for local setup.
- Keep model files (`models/*.pkl`, `models/*.json`) committed so inference works in production.
- For a strict final deployment checklist, use `RENDER_PREFLIGHT.md`.

## Optional model scripts

Retrain model:

```bash
python scripts/trained_model.py
```

Evaluate model:

```bash
python scripts/evaluate_lifestyle_model.py
```

## Security/production checklist

- Use a strong `FLASK_SECRET`
- Use managed PostgreSQL with restricted access
- Keep API keys in Render env vars only
- Prefer HTTPS-only cookies at proxy level (Render default HTTPS)
- Rotate keys if leaked

## Disclaimer

This project is a wellness screening tool and not a medical diagnosis system.
