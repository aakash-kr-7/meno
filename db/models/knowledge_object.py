# Core ORM model — every stored piece of intelligence. type drives retrieval and ranking half-life. embedding is a 384-dim pgvector vector. source_context JSONB records where it came from.
"""
Core ORM model — every stored piece of intelligence. type drives retrieval and ranking half-life. embedding is a 384-dim pgvector vector. source_context JSONB records where it came from.
"""

from sqlalchemy import Column, String, Text, Integer, Float, DateTime, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector

from db.base import Base
from core.types import KnowledgeType


class KnowledgeObject(Base):
    __tablename__ = "knowledge_objects"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    source_type = Column(String, nullable=True)
    source_id = Column(String, nullable=True)
    source_context = Column(JSONB, nullable=False, server_default=text("'{}'"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    last_accessed = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    access_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    confidence = Column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    importance = Column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    metadata_ = Column("metadata", JSONB, nullable=False, server_default=text("'{}'"))
    tags = Column(ARRAY(Text), nullable=False, server_default=text("'{}'"))

    __table_args__ = (
        CheckConstraint(
            f"type IN ({', '.join(repr(t.value) for t in KnowledgeType)})",
            name="check_knowledge_type"
        ),
        Index("idx_knowledge_objects_embedding", "embedding", postgresql_using="ivfflat", postgresql_ops={"embedding": "vector_cosine_ops"}),
        Index("idx_ko_tenant_user_type", "tenant_id", "user_id", "type"),
        Index("idx_ko_source_type_id", "source_type", "source_id"),
        Index("idx_ko_tags_gin", "tags", postgresql_using="gin"),
    )
