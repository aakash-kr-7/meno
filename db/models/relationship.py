# Graph edges. Relationships are first-class — enable walking the graph, surfacing contradictions.
"""
Graph edges. Relationships are first-class — enable walking the graph, surfacing contradictions.
"""

from sqlalchemy import Column, String, Text, Float, DateTime, Boolean, ForeignKey, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID

from db.base import Base
from core.types import RelationshipType


class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id = Column(String, nullable=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_objects.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False, default=0.5, server_default=text("0.5"))
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    inferred = Column(Boolean, nullable=False, default=False, server_default=text("false"))

    __table_args__ = (
        CheckConstraint("source_id != target_id", name="check_no_self_loops"),
        CheckConstraint(
            f"relationship_type IN ({', '.join(repr(t.value) for t in RelationshipType)})",
            name="check_relationship_type"
        ),
        Index("idx_rel_tenant_type", "tenant_id", "relationship_type"),
    )
