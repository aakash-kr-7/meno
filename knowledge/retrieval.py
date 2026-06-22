# Semantic retrieval engine. pgvector cosine search fi type-aware re-ranking fi optional relationship expansion. Context scoping prevents mixing unrelated projects.
"""
Semantic retrieval engine. pgvector cosine search fi type-aware re-ranking fi optional relationship expansion. Context scoping prevents mixing unrelated projects.
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.embeddings import embedding_service
from core.ranking import RankInput, rank_many
from db.models.knowledge_object import KnowledgeObject
from db.models.context import KnowledgeInContext
from knowledge.store import update_access


async def retrieve_knowledge(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    query: str,
    top_k: int = 5,
    knowledge_type: Optional[str] = None,
    context_id: Optional[Any] = None,
    expand_relationships: bool = False,
    relationship_types: List[str] = []
) -> List[Dict[str, Any]]:
    # 1. Embed query
    query_vector = embedding_service.embed(query)

    # 2. pgvector cosine query
    sim_expr = (1.0 - KnowledgeObject.embedding.cosine_distance(query_vector)).label("similarity")
    stmt = select(KnowledgeObject, sim_expr).where(
        KnowledgeObject.tenant_id == tenant_id,
        KnowledgeObject.user_id == user_id
    )

    if knowledge_type:
        stmt = stmt.where(KnowledgeObject.type == knowledge_type)

    if context_id:
        ctx_uuid = uuid.UUID(context_id) if isinstance(context_id, str) else context_id
        subq = select(KnowledgeInContext.knowledge_object_id).where(KnowledgeInContext.context_id == ctx_uuid)
        stmt = stmt.where(KnowledgeObject.id.in_(subq))

    # Fetch extra (top_k * 3) for re-ranking
    stmt = stmt.order_by(KnowledgeObject.embedding.cosine_distance(query_vector)).limit(top_k * 3)
    res = await db.execute(stmt)
    rows = res.all()

    if not rows:
        return []

    # 3. Build RankInput per row, call rank_many()
    inputs = []
    for obj, similarity in rows:
        inputs.append(RankInput(
            similarity=float(similarity) if similarity is not None else 0.0,
            knowledge_type=obj.type,
            created_at=obj.created_at,
            access_count=obj.access_count or 0,
            confidence=obj.confidence or 0.5,
            in_query_context=True
        ))

    ranked = rank_many(inputs)
    top_ranked = ranked[:top_k]

    # Lazy import to avoid potential circular imports
    from knowledge.relationships import get_subgraph

    # 4. update_access for returned objects
    # 5. Optional relationship expansion
    # 6. Return list of serializable dicts
    results = []
    for index, rank_res in top_ranked:
        obj, similarity = rows[index]
        await update_access(db, obj.id)

        obj_dict = {
            "id": str(obj.id),
            "type": obj.type,
            "title": obj.title,
            "content": obj.content,
            "score": rank_res.score,
            "breakdown": rank_res.breakdown,
            "source_type": obj.source_type,
            "source_id": obj.source_id,
            "source_context": obj.source_context,
            "confidence": obj.confidence,
            "tags": obj.tags,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
        }

        if expand_relationships:
            subgraph = await get_subgraph(db, obj.id, max_depth=1, relationship_types=relationship_types)
            obj_dict["relationships"] = subgraph
        else:
            obj_dict["relationships"] = None

        results.append(obj_dict)

    return results


async def search_by_type(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    knowledge_type: str,
    context_id: Optional[Any] = None,
    limit: int = 50
) -> List[KnowledgeObject]:
    stmt = select(KnowledgeObject).where(
        KnowledgeObject.tenant_id == tenant_id,
        KnowledgeObject.user_id == user_id,
        KnowledgeObject.type == knowledge_type
    )

    if context_id:
        ctx_uuid = uuid.UUID(context_id) if isinstance(context_id, str) else context_id
        subq = select(KnowledgeInContext.knowledge_object_id).where(KnowledgeInContext.context_id == ctx_uuid)
        stmt = stmt.where(KnowledgeObject.id.in_(subq))

    stmt = stmt.order_by(KnowledgeObject.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
