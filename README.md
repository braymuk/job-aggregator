# Job Aggregator (Daily Digest MVP)

Minimal Python/Postgres implementation for one feature: daily email digest of matching jobs posted in the last 24 hours.

Deployment direction is documented in [`docs/DEPLOYMENT_PLAN.md`](docs/DEPLOYMENT_PLAN.md):
AWS Lambda + EventBridge Scheduler + Neon Postgres + Amazon SES.

## What this includes

- `job_postings` schema via SQLAlchemy model
- pluggable ingestion sources:
  - generic VC board parser (`sequoia`, `a16z`, `lvsp`)
  - Accel-specific parser placeholder
  - LinkedIn/Apple/Google parser placeholders
  - optional skeleton source for local testing
- matching logic (keywords + remote/location)
- digest query: matched jobs where `posted_at >= now - 24h`
- email sender (SMTP)

## Setup

1. Create and activate a virtualenv.
2. Install deps:

```bash
pip install -e .
```

3. Copy env file and update values:

```bash
cp .env.example .env
```

4. Export environment variables from `.env` in your shell.

Optional local config file (easier in PyCharm):

```bash
cp config.local.json.example config.local.json
```

Config precedence is:

1. Environment variables
2. `config.local.json`
3. Built-in defaults

## Run once

```bash
python -m job_aggregator.main
```

Or with console script:

```bash
job-digest
```

## Daily schedule (cron)

Example: run every day at 8:00 AM.

```cron
0 8 * * * cd /Users/braymuk/Projects/job-aggregator && /path/to/venv/bin/job-digest >> /tmp/job-digest.log 2>&1
```

## Local-first development

Build and test locally first, then deploy with the same environment variable names.

```bash
cd /Users/braymuk/Projects/job-aggregator
set -a; source .env; set +a
PYTHONPATH=src python3 -m job_aggregator.main
```

To keep local runs deterministic while connectors are under development:

- `INGEST_ENABLE_REAL_SOURCES=false`
- `INGEST_ENABLE_SKELETON_SOURCE=true`

When you want to test real connectors:

- `INGEST_ENABLE_REAL_SOURCES=true`
- `INGEST_ENABLE_PLACEHOLDER_SOURCES=false` (default, to avoid unimplemented source stubs)

## Next step for ingestion

Replace `SkeletonSourceClient` in `src/job_aggregator/ingest.py` with real source clients that implement:

```python
def fetch_recent_jobs(self) -> Iterable[IncomingJobPosting]:
    ...
```
