# ORM for knowledge_context and knowledge_in_context. Scopes knowledge to project/team/org.
"""
ORM for knowledge_context and knowledge_in_context. Scopes knowledge to project/team/org.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from db.base import Base


class KnowledgeContext(Base):
    __tablename__ = "knowledge_context"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(String, nullable=False)
    context_type = Column(String, nullable=False)
    context_id = Column(String, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "context_type", "context_id", name="uq_context_tenant_type_id"),
    )


class KnowledgeInContext(Base):
    __tablename__ = "knowledge_in_context"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    knowledge_object_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_objects.id", ondelete="CASCADE"), nullable=False)
    context_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_context.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("knowledge_object_id", "context_id", name="uq_ko_in_context"),
    )
