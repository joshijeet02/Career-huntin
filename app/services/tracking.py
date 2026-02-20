import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ExecutionEvent, JobRecord

TRACKING_PATH = Path(__file__).resolve().parents[2] / "data" / "tracker_snapshot.csv"


def export_tracking_snapshot(db: Session) -> str:
    TRACKING_PATH.parent.mkdir(parents=True, exist_ok=True)
    events = db.scalars(
        select(ExecutionEvent).order_by(ExecutionEvent.created_at.desc(), ExecutionEvent.id.desc())
    ).all()

    with TRACKING_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "event_id",
                "created_at_utc",
                "job_id",
                "company",
                "title",
                "event_type",
                "channel",
                "status",
                "attempt",
                "error_message",
            ]
        )
        for event in events:
            job = db.get(JobRecord, event.job_id)
            writer.writerow(
                [
                    event.id,
                    event.created_at.isoformat(),
                    event.job_id,
                    job.company if job else "",
                    job.title if job else "",
                    event.event_type,
                    event.channel,
                    event.status,
                    event.attempt,
                    event.error_message or "",
                ]
            )
    return str(TRACKING_PATH)

