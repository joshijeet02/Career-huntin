# Job Search Automation MVP

FastAPI backend implementing a high-automation, batch-approval job search workflow:

- profile + CV ingestion
- job discovery + dedupe + scoring
- CV/cover letter/outreach draft generation
- daily review queue with approve/reject/defer decisions
- post-approval execution with compliance checks and audit logs
- funnel analytics

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test

```bash
pytest -q
```

## API

- `POST /ingest/profile`
- `POST /jobs/discover/run`
- `GET /jobs/queue?status=pending_review`
- `POST /review/batch/{id}/decision`
- `POST /execute/plan/{id}`
- `GET /analytics/funnel`
- `POST /orchestrator/run-daily`
- `GET /tracking/snapshot-path`
- `GET /dashboard`
- `GET /dashboard/data`

## Notes

- External connectors are intentionally simulated in this MVP.
- Batch approval is mandatory before execution.
- Compliance controls include suppression lists, rate limits, and uniqueness checks.
- Autonomous mode reads `/Users/jeetjoshi/Documents/New project/data/candidate_intelligence_v1.json` and auto-executes only when one-time written approval is enabled there.
- Tracker snapshots are exported to `/Users/jeetjoshi/Documents/New project/data/tracker_snapshot.csv` (Google Sheets import-ready CSV).
- Dashboard UI is available at `/dashboard` with auto-refresh every 30 seconds and one-click daily run trigger.
- Dashboard supports filters (`source`, `geography`, `role_family`, `status`) and includes a dedicated Top Targets panel for VC/consulting/high-pay opportunities.
