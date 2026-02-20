from sqlalchemy.orm import Session

from app.models import AuditLog


def log_event(db: Session, entity_type: str, entity_id: int, action: str, details: dict) -> None:
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(entry)

