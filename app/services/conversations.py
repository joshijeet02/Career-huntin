from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import CoachConversation
from app.schemas import CoachConversationHistoryItem


class ConversationCrypto:
    def __init__(self) -> None:
        key = self._resolve_key()
        try:
            self._fernet = Fernet(key)
        except ValueError:
            fallback_seed = os.getenv("BACKEND_API_KEY", "").strip() or "development-only-default-key"
            digest = hashlib.sha256(fallback_seed.encode("utf-8")).digest()
            self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def _resolve_key(self) -> bytes:
        explicit = os.getenv("APP_ENCRYPTION_KEY", "").strip()
        if explicit:
            return explicit.encode("utf-8")

        fallback_seed = os.getenv("BACKEND_API_KEY", "").strip() or "development-only-default-key"
        digest = hashlib.sha256(fallback_seed.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return "[decryption-failed]"


class ConversationStore:
    def __init__(self) -> None:
        self._crypto = ConversationCrypto()

    def save_turn(
        self,
        db: Session,
        *,
        user_id: str,
        session_id: str,
        intent: str,
        user_message: str,
        coach_message: str,
        context: str,
        coach_model: str,
    ) -> CoachConversation:
        retention_days = int(os.getenv("COACH_RETENTION_DAYS", "90"))
        expires_at = datetime.utcnow() + timedelta(days=max(retention_days, 1))

        row = CoachConversation(
            user_id=user_id,
            session_id=session_id,
            intent=intent,
            user_message_enc=self._crypto.encrypt(user_message),
            coach_message_enc=self._crypto.encrypt(coach_message),
            context_enc=self._crypto.encrypt(context),
            coach_model=coach_model,
            retention_expires_at=expires_at,
        )
        db.add(row)
        db.flush()
        return row

    def list_history(
        self,
        db: Session,
        *,
        user_id: str,
        session_id: str | None,
        limit: int,
    ) -> list[CoachConversationHistoryItem]:
        stmt = select(CoachConversation).where(CoachConversation.user_id == user_id)
        if session_id:
            stmt = stmt.where(CoachConversation.session_id == session_id)
        rows = db.scalars(stmt.order_by(CoachConversation.created_at.desc()).limit(limit)).all()

        out: list[CoachConversationHistoryItem] = []
        for row in rows:
            out.append(
                CoachConversationHistoryItem(
                    id=row.id,
                    user_id=row.user_id,
                    session_id=row.session_id,
                    intent=row.intent,
                    user_message=self._crypto.decrypt(row.user_message_enc),
                    coach_message=self._crypto.decrypt(row.coach_message_enc),
                    created_at=row.created_at,
                )
            )
        return out

    def purge_expired(self, db: Session) -> int:
        now = datetime.utcnow()
        stmt = delete(CoachConversation).where(CoachConversation.retention_expires_at < now)
        result = db.execute(stmt)
        return int(result.rowcount or 0)
