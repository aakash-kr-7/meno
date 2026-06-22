# Knowledge write path. Validates type, embeds content, inserts into knowledge_objects, links contexts. Called by both API and promotion worker.
"""
Knowledge write path. Validates type, embeds content, inserts into knowledge_objects, links contexts. Called by both API and promotion worker.
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.types import KnowledgeType
from core.embeddings import embedding_service
from db.models.knowledge_object import KnowledgeObject
from db.models.context import KnowledgeInContext


async def store_knowledge_object(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    type: str,
    content: str,
    title: Optional[str] = None,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    source_context: Dict[str, Any] = {},
    confidence: float = 0.5,
    tags: List[str] = [],
    metadata: Dict[str, Any] = {},
    context_ids: List[Any] = []
) -> KnowledgeObject:
    # 1. Validate type in KnowledgeType
    if type not in [t.value for t in KnowledgeType]:
        raise ValueError(f"Invalid knowledge type: {type}")

    # 2. embedding_service.embed(content)
    embedding = embedding_service.embed(content)

    # 3. Insert KnowledgeObject row
    obj = KnowledgeObject(
        tenant_id=tenant_id,
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        embedding=embedding,
        source_type=source_type,
        source_id=source_id,
        source_context=source_context,
        confidence=confidence,
        tags=tags,
        metadata_=metadata
    )
    db.add(obj)
    await db.flush()  # Populate obj.id

    # 4. For each context_id, insert KnowledgeInContext (ignore conflict)
    for ctx_id in context_ids:
        ctx_uuid = uuid.UUID(ctx_id) if isinstance(ctx_id, str) else ctx_id
        stmt = pg_insert(KnowledgeInContext).values(
            knowledge_object_id=obj.id,
            context_id=ctx_uuid
        ).on_conflict_do_nothing(constraint="uq_ko_in_context")
        await db.execute(stmt)

    # 5. Commit, refresh, return
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_access(db: AsyncSession, object_id: Any) -> None:
    obj_uuid = uuid.UUID(object_id) if isinstance(object_id, str) else object_id
    stmt = (
        update(KnowledgeObject)
        .where(KnowledgeObject.id == obj_uuid)
        .values(
            last_accessed=text("now()"),
            access_count=KnowledgeObject.access_count + 1
        )
    )
    await db.execute(stmt)
    await db.commit()


async def get_knowledge_object(db: AsyncSession, object_id: Any) -> Optional[KnowledgeObject]:
    obj_uuid = uuid.UUID(object_id) if isinstance(object_id, str) else object_id
    stmt = select(KnowledgeObject).where(KnowledgeObject.id == obj_uuid)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
