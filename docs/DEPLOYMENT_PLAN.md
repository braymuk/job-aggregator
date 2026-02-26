# Deployment Plan

## Approved Architecture

1. Compute: AWS Lambda
2. Scheduler: Amazon EventBridge Scheduler (once per day)
3. Database: Neon Postgres
4. Email: Amazon SES (SMTP credentials)
5. Secrets: AWS Secrets Manager (or Lambda environment variables for early stage)

## Why This Stack

1. No always-on server to manage.
2. Very low cost for once-daily execution.
3. Clear path from local development to production.

## Runtime Flow

1. EventBridge triggers Lambda on schedule.
2. Lambda executes `run_daily_flow()`.
3. App ingests jobs, computes matches, queries last 24h matches, and sends digest via SES SMTP.
4. Lambda logs execution summary to CloudWatch.

## Local Development (Keep This Workflow)

Continue building and testing locally first, then deploy unchanged core logic.

1. Local DB: Postgres on `localhost:5432` (or SQLite fallback for quick tests)
2. Local email: SMTP dev server on `localhost:1025`
3. Non-secret local defaults can live in `config.local.json`
4. Local run command:

```bash
cd /Users/braymuk/Projects/job-aggregator
set -a; source .env; set +a
PYTHONPATH=src python3 -m job_aggregator.main
```

## Environment Variable Strategy

Use the same variable names locally and in Lambda:

1. `DATABASE_URL`
2. `DIGEST_EMAIL_TO`
3. `DIGEST_EMAIL_FROM`
4. `DIGEST_SMTP_HOST`
5. `DIGEST_SMTP_PORT`
6. `DIGEST_SMTP_USERNAME`
7. `DIGEST_SMTP_PASSWORD`
8. `DIGEST_USE_TLS`
9. `PREFERENCE_KEYWORDS`
10. `PREFERENCE_LOCATION`
11. `PREFERENCE_REMOTE_ONLY`

For local convenience, these can also be placed in `config.local.json`. In production,
prefer environment variables / Secrets Manager.

## Next Deployment Tasks (When Ready)

1. Add Lambda handler wrapper that calls `run_daily_flow()`.
2. Package app for Lambda (zip or container).
3. Create EventBridge schedule expression (daily).
4. Provision Neon database and set `DATABASE_URL`.
5. Create SES SMTP credentials and set SMTP env vars.
6. Add CloudWatch alerts for failures.
