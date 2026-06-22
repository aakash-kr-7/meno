# Relationship graph operations. Explicit edges. get_subgraph() does BFS. Enables 'what depends on X?' queries.
"""
Relationship graph operations. Explicit edges. get_subgraph() does BFS. Enables 'what depends on X?' queries.
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.types import RelationshipType
from db.models.relationship import KnowledgeRelationship
from db.models.knowledge_object import KnowledgeObject


async def create_relationship(
    db: AsyncSession,
    tenant_id: Optional[str],
    source_id: Any,
    target_id: Any,
    relationship_type: str,
    confidence: float = 1.0,
    explanation: Optional[str] = None,
    inferred: bool = False
) -> KnowledgeRelationship:
    # Validate relationship_type in RelationshipType
    if relationship_type not in [t.value for t in RelationshipType]:
        raise ValueError(f"Invalid relationship type: {relationship_type}")

    src_uuid = uuid.UUID(source_id) if isinstance(source_id, str) else source_id
    tgt_uuid = uuid.UUID(target_id) if isinstance(target_id, str) else target_id

    # Validate source != target
    if src_uuid == tgt_uuid:
        raise ValueError("Source and target IDs must be different; self-loops are not allowed.")

    rel = KnowledgeRelationship(
        tenant_id=tenant_id,
        source_id=src_uuid,
        target_id=tgt_uuid,
        relationship_type=relationship_type,
        confidence=confidence,
        explanation=explanation,
        inferred=inferred
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return rel


async def get_relationships(
    db: AsyncSession,
    object_id: Any,
    direction: str = "both",
    relationship_types: List[str] = []
) -> Dict[str, List[Dict[str, Any]]]:
    obj_uuid = uuid.UUID(object_id) if isinstance(object_id, str) else object_id

    outgoing_list = []
    if direction in ("outgoing", "both"):
        stmt = select(KnowledgeRelationship, KnowledgeObject.title).join(
            KnowledgeObject, KnowledgeRelationship.target_id == KnowledgeObject.id
        ).where(KnowledgeRelationship.source_id == obj_uuid)
        if relationship_types:
            stmt = stmt.where(KnowledgeRelationship.relationship_type.in_(relationship_types))
        res = await db.execute(stmt)
        for rel, title in res.all():
            outgoing_list.append({
                "id": str(rel.id),
                "tenant_id": rel.tenant_id,
                "source_id": str(rel.source_id),
                "target_id": str(rel.target_id),
                "target_title": title,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence,
                "explanation": rel.explanation,
                "inferred": rel.inferred,
                "created_at": rel.created_at.isoformat() if rel.created_at else None
            })

    incoming_list = []
    if direction in ("incoming", "both"):
        stmt = select(KnowledgeRelationship, KnowledgeObject.title).join(
            KnowledgeObject, KnowledgeRelationship.source_id == KnowledgeObject.id
        ).where(KnowledgeRelationship.target_id == obj_uuid)
        if relationship_types:
            stmt = stmt.where(KnowledgeRelationship.relationship_type.in_(relationship_types))
        res = await db.execute(stmt)
        for rel, title in res.all():
            incoming_list.append({
                "id": str(rel.id),
                "tenant_id": rel.tenant_id,
                "source_id": str(rel.source_id),
                "target_id": str(rel.target_id),
                "source_title": title,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence,
                "explanation": rel.explanation,
                "inferred": rel.inferred,
                "created_at": rel.created_at.isoformat() if rel.created_at else None
            })

    return {
        "outgoing": outgoing_list,
        "incoming": incoming_list
    }


async def get_subgraph(
    db: AsyncSession,
    object_id: Any,
    max_depth: int = 2,
    relationship_types: List[str] = []
) -> Dict[str, Any]:
    root_uuid = uuid.UUID(object_id) if isinstance(object_id, str) else object_id

    visited_nodes = {root_uuid}
    queue = [(root_uuid, 0)]
    edges = {}

    while queue:
        curr_id, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        stmt = select(KnowledgeRelationship).where(
            (KnowledgeRelationship.source_id == curr_id) | (KnowledgeRelationship.target_id == curr_id)
        )
        if relationship_types:
            stmt = stmt.where(KnowledgeRelationship.relationship_type.in_(relationship_types))
        res = await db.execute(stmt)
        rels = res.scalars().all()

        for rel in rels:
            edges[rel.id] = rel
            neighbor = rel.target_id if rel.source_id == curr_id else rel.source_id
            if neighbor not in visited_nodes:
                visited_nodes.add(neighbor)
                queue.append((neighbor, depth + 1))

    nodes_list = []
    if visited_nodes:
        stmt_nodes = select(KnowledgeObject).where(KnowledgeObject.id.in_(visited_nodes))
        res_nodes = await db.execute(stmt_nodes)
        for node in res_nodes.scalars().all():
            nodes_list.append({
                "id": str(node.id),
                "type": node.type,
                "title": node.title,
                "content_snippet": node.content[:100] if node.content else ""
            })

    edges_list = []
    for rel in edges.values():
        edges_list.append({
            "id": str(rel.id),
            "source": str(rel.source_id),
            "target": str(rel.target_id),
            "type": rel.relationship_type,
            "confidence": rel.confidence,
            "explanation": rel.explanation,
            "inferred": rel.inferred
        })

    return {
        "root": str(root_uuid),
        "nodes": nodes_list,
        "edges": edges_list
    }


async def delete_relationship(db: AsyncSession, relationship_id: Any) -> bool:
    rel_uuid = uuid.UUID(relationship_id) if isinstance(relationship_id, str) else relationship_id
    stmt = select(KnowledgeRelationship).where(KnowledgeRelationship.id == rel_uuid)
    res = await db.execute(stmt)
    rel = res.scalar_one_or_none()
    if rel:
        await db.delete(rel)
        await db.commit()
        return True
    return False
