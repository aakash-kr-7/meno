# Context management. Scopes knowledge to project/team/org. Prevents leakage between unrelated work.
"""
Context management. Scopes knowledge to project/team/org. Prevents leakage between unrelated work.
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.types import ContextType
from db.models.context import KnowledgeContext, KnowledgeInContext
from db.models.knowledge_object import KnowledgeObject


async def define_context(
    db: AsyncSession,
    tenant_id: str,
    context_type: str,
    context_id_str: str,
    metadata: Dict[str, Any] = {}
) -> KnowledgeContext:
    # Validate context_type in ContextType
    if context_type not in [t.value for t in ContextType]:
        raise ValueError(f"Invalid context type: {context_type}")

    # Upsert context
    stmt = pg_insert(KnowledgeContext).values(
        tenant_id=tenant_id,
        context_type=context_type,
        context_id=context_id_str,
        metadata_=metadata
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_context_tenant_type_id",
        set_={
            "metadata": stmt.excluded.metadata,
            "updated_at": text("now()")
        }
    )
    await db.execute(stmt)
    await db.commit()

    # Retrieve and return context
    stmt_select = select(KnowledgeContext).where(
        KnowledgeContext.tenant_id == tenant_id,
        KnowledgeContext.context_type == context_type,
        KnowledgeContext.context_id == context_id_str
    )
    res = await db.execute(stmt_select)
    return res.scalar_one()


async def get_context(
    db: AsyncSession,
    tenant_id: str,
    context_type: str,
    context_id_str: str
) -> Optional[KnowledgeContext]:
    stmt = select(KnowledgeContext).where(
        KnowledgeContext.tenant_id == tenant_id,
        KnowledgeContext.context_type == context_type,
        KnowledgeContext.context_id == context_id_str
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def link_to_context(
    db: AsyncSession,
    knowledge_object_id: Any,
    context_uuid: Any
) -> None:
    ko_uuid = uuid.UUID(knowledge_object_id) if isinstance(knowledge_object_id, str) else knowledge_object_id
    ctx_uuid = uuid.UUID(context_uuid) if isinstance(context_uuid, str) else context_uuid

    stmt = pg_insert(KnowledgeInContext).values(
        knowledge_object_id=ko_uuid,
        context_id=ctx_uuid
    ).on_conflict_do_nothing(constraint="uq_ko_in_context")
    await db.execute(stmt)
    await db.commit()


async def get_knowledge_in_context(
    db: AsyncSession,
    context_uuid: Any,
    limit: int = 100
) -> List[KnowledgeObject]:
    ctx_uuid = uuid.UUID(context_uuid) if isinstance(context_uuid, str) else context_uuid

    stmt = select(KnowledgeObject).join(
        KnowledgeInContext,
        KnowledgeObject.id == KnowledgeInContext.knowledge_object_id
    ).where(
        KnowledgeInContext.context_id == ctx_uuid
    ).limit(limit)

    res = await db.execute(stmt)
    return list(res.scalars().all())
