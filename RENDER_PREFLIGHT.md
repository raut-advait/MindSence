# Render Preflight Checklist (Final)

Use this as a final copy/paste checklist before pressing **Deploy**.

## 1) Render Service Setup

- Runtime: **Python 3**
- Build Command:
  - `pip install -r requirements.txt`
- Start Command:
  - `gunicorn app:app --bind 0.0.0.0:$PORT`
- If using Blueprint (`render.yaml`), PostgreSQL is provisioned and `DATABASE_URL` is auto-connected.

## 2) Required Environment Variables (Render)

Add these exact keys in **Render → Environment**:

- `FLASK_SECRET` = `<strong-random-secret>`
- `GROQ_API_KEY` = `<your-groq-api-key>`

Optional:

- `GROQ_MODEL` = `llama-3.1-8b-instant`

## 3) Quick Validation Rules

- `DATABASE_URL` must start with `postgresql://` (or `postgres://`, auto-normalized).
- `FLASK_SECRET` must be set in production (do not rely on default).
- `models/trained_model.pkl`, `models/preprocessor.pkl`, `models/features.json`, `models/metadata.json` must be present in repo.
- Do **not** use local `.env.local` values on Render; use Render env settings only.
- Use `.env.example` as the source of truth for local env setup.

## 4) Health Smoke Test After Deploy

- Open app root URL and verify page loads.
- Login/register flow works.
- Submit one assessment and confirm result page loads.
- Open Analytics page and confirm API-backed cards/charts populate.

## 5) If Deploy Fails (Fast Triage)

- Boot failure with DB error:
  - Recheck `DATABASE_URL` value and protocol.
- AI summary/chat not working:
  - Recheck `GROQ_API_KEY` and optional `GROQ_MODEL`.
- Session/auth issues:
  - Recheck `FLASK_SECRET` is set and non-empty.

---

## Ready-to-Paste Render Config Block

Build command:

`pip install -r requirements.txt`

Start command:

`gunicorn app:app --bind 0.0.0.0:$PORT`

Environment keys:

- `FLASK_SECRET`
- `GROQ_API_KEY`
- `GROQ_MODEL` (optional)
