# ORM for sessions and session_messages. Tier 0 working memory. Postgres = source of truth; Redis = cache.
"""
ORM for sessions and session_messages. Tier 0 working memory. Postgres = source of truth; Redis = cache.
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from db.base import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    last_activity = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    promoted = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    promoted_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    metadata_ = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="check_session_message_role"),
    )
