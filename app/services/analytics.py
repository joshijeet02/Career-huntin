from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ExecutionEvent
from app.schemas import AnalyticsFunnelResponse


def funnel(db: Session) -> AnalyticsFunnelResponse:
    applied = db.scalar(
        select(func.count())
        .select_from(ExecutionEvent)
        .where(ExecutionEvent.event_type == "application", ExecutionEvent.status == "success")
    ) or 0
    replied = db.scalar(
        select(func.count())
        .select_from(ExecutionEvent)
        .where(ExecutionEvent.event_type == "reply", ExecutionEvent.status == "success")
    ) or 0
    interview = db.scalar(
        select(func.count())
        .select_from(ExecutionEvent)
        .where(ExecutionEvent.event_type == "interview", ExecutionEvent.status == "success")
    ) or 0
    offers = db.scalar(
        select(func.count())
        .select_from(ExecutionEvent)
        .where(ExecutionEvent.event_type == "offer", ExecutionEvent.status == "success")
    ) or 0
    return AnalyticsFunnelResponse(applied=applied, replied=replied, interview=interview, offers=offers)

