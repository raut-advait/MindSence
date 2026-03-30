# Render Preflight Checklist (Current)

Use this checklist right before deploying the current version.

## 1) Render service setup

- Runtime: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
- If using `render.yaml`, PostgreSQL is provisioned and `DATABASE_URL` is auto-wired.

## 2) Required environment variables

Set in Render Environment:

- `FLASK_SECRET` = strong random value
- `GROQ_API_KEY` = valid Groq key

Optional:

- `GROQ_MODEL` = `llama-3.1-8b-instant`

## 3) Required model artifacts

Ensure these files exist in repo before deploy:

- `models/quick_model.pkl`
- `models/quick_preprocessor.pkl`
- `models/quick_metadata.json`
- `models/quick_features.json`
- `models/severity_model.pkl`
- `models/severity_preprocessor.pkl`
- `models/severity_metadata.json`
- `models/severity_features.json`

## 4) Required pre-deploy DB step

Run DB initialization/migration once against the target database before first traffic:

```bash
python -c "from db_helpers import init_db; print('init_db:', init_db())"
```

This ensures additive columns used by current full-assessment saves are present.

## 5) Safety checks

- `DATABASE_URL` starts with `postgresql://` or `postgres://`
- `FLASK_SECRET` is set (never rely on default in production)
- `.env.local` values are not used on Render

## 6) Post-deploy smoke test

1. Open home page and login/register
2. Submit one quick assessment and one full assessment
3. Verify result page renders
4. Verify History table/charts load
5. Verify Analytics table/charts load
6. Verify AI Summary loads and Refresh Summary works

## 7) Fast triage

- Boot fails with DB error: verify `DATABASE_URL` and run pre-deploy DB step
- AI summary/chat fails: verify `GROQ_API_KEY` and optional `GROQ_MODEL`
- Auth/session issues: verify non-empty `FLASK_SECRET`
